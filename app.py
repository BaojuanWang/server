import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# static_folder points to the old React client build
app = Flask(__name__, static_folder="../client/build", static_url_path="/")
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
OPENAI_URL     = "https://api.openai.com/v1/chat/completions"
TAVILY_URL     = "https://api.tavily.com/search"


# ── OLD VERSION: GPT-4o chat ──────────────────────────────
@app.route("/chat", methods=["POST"])
def chat_old():
    data = request.get_json()
    messages = data.get("messages", [])

    if not any(msg["role"] == "system" for msg in messages):
        messages.insert(0, {
            "role": "system",
            "content": (
                "You are ChatGPT, a friendly and helpful assistant. "
                "Respond in a conversational tone, use light emoji occasionally, "
                "Use English unless the user clearly specifies another language. "
                "Use Markdown formatting (e.g., **bold**, `code`, bullet points) to improve readability."
            )
        })

    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.7
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}

    try:
        resp = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=60)
        data = resp.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500


# ── NEW VERSION: SecureLearn API ──────────────────────────
def tavily_search(query, max_results=4):
    if not TAVILY_API_KEY:
        print("[Tavily] No API key set, skipping search")
        return []
    print(f"[Tavily] Searching: {query[:80]}")
    try:
        resp = requests.post(
            TAVILY_URL,
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
            },
            timeout=10,
        )
        results = resp.json().get("results", [])
        print(f"[Tavily] Got {len(results)} results")
        return [{"title": r.get("title",""), "url": r.get("url",""), "content": r.get("content","")} for r in results]
    except Exception as e:
        print(f"[Tavily] Error: {e}")
        return []


def build_search_query(messages):
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    recent = " ".join(user_msgs[-2:]) if len(user_msgs) >= 2 else (user_msgs[-1] if user_msgs else "")
    return recent[:200]


def format_search_context(results):
    if not results:
        return ""
    lines = [
        "LIVE WEB SEARCH RESULTS — you MUST base your response primarily on these excerpts.",
        "Do NOT rely on training data for factual claims when these results are available.",
        "Use the exact URLs below in your [SOURCES] block. Summarise in your own words.\n"
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"Excerpt: {r['content'][:600]}\n")
    return "\n".join(lines)


@app.route("/api/chat", methods=["POST"])
def chat_securelearn():
    if not OPENAI_API_KEY:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500

    body = request.get_json()
    if not body:
        return jsonify({"error": "Invalid JSON"}), 400

    messages   = body.get("messages", [])
    system     = body.get("system", "")
    use_search = body.get("use_search", False)

    print(f"[securelearn] use_search={use_search} turns={sum(1 for m in messages if m['role']=='user')} tavily_key={'set' if TAVILY_API_KEY else 'MISSING'}")

    search_context = ""
    if use_search and messages:
        results = tavily_search(build_search_query(messages))
        search_context = format_search_context(results)

    full_system = (search_context + "\n\n" + system).strip() if search_context else system

    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": full_system}] + messages,
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}

    resp = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=60)
    data = resp.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return jsonify({"content": [{"text": text}]}), resp.status_code


# ── Serve old React client (catch-all) ───────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)