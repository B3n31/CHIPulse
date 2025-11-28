import os
from flask import Flask, request, jsonify, send_from_directory
from llm_router import answer_with_db_tools   # ← 关键：把 router 引进来

app = Flask(__name__)

# 前端目录：scripts/../front-end
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "front-end")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/script.js")
def script_js():
    return send_from_directory(FRONTEND_DIR, "script.js")


@app.route("/style.css")
def style_css():
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json(force=True) or {}
    q = (data.get("prompt") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "Empty prompt"}), 400

    try:
        answer = answer_with_db_tools(q)
        return jsonify({"ok": True, "text": answer})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(force=True) or {}
    user_prompt = data.get("prompt", "")
    try:
        text = answer_with_db_tools(user_prompt)
        return jsonify({"ok": True, "text": text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
