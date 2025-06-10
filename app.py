from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
import os

from dotenv import load_dotenv
load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ 添加前端打包路径（React build 文件夹）
app = Flask(__name__, static_folder="../client/build", static_url_path="/")
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    messages = data.get("messages")

    # 💡 如果没有 system prompt，插入一个美化版
    if not any(msg["role"] == "system" for msg in messages):
        messages.insert(0, {
            "role": "system",
            "content": (
                "You are ChatGPT, a friendly and helpful assistant. "
                "Respond in a conversational tone, use light emoji occasionally, "
                "and format your responses using Markdown when appropriate "
                "(e.g., **bold**, bullet points, code blocks)."
            )
        })

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

# ✅ 为部署前端设置主页访问
@app.route("/")
def serve():
    return send_from_directory(app.static_folder, "index.html")

# ✅ 捕捉所有其他路径，交由 React 前端路由处理
@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, "index.html")

# ✅ Flask 监听公网 IP，支持部署
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
