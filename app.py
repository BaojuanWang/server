import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="../client/build", static_url_path="/")
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_URL     = "https://api.openai.com/v1/chat/completions"


# ── SecureLearn API ───────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat_securelearn():
    if not OPENAI_API_KEY:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500

    body = request.get_json()
    if not body:
        return jsonify({"error": "Invalid JSON"}), 400

    messages = body.get("messages", [])
    system   = body.get("system", "")

    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": system}] + messages,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    resp = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=60)
    data = resp.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return jsonify({"content": [{"text": text}]}), resp.status_code


# ── Serve React client (catch-all) ───────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)