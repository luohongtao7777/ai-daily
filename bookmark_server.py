#!/usr/bin/env python3
"""Bookmark API 服务 — 接收 GitHub 项目收藏/取消收藏
   路径说明：nginx 已将 /api/ 代理到本服务，路径前缀已被剥离"""
import json, os
from http.server import HTTPServer, BaseHTTPRequestHandler

# 复用已有的书签文件位置
DATA_FILE = "/home/ubuntu/bookmarks/bookmarks.json"
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


def load():
    if os.path.exists(DATA_FILE):
        try:
            data = json.loads(open(DATA_FILE, "r", encoding="utf-8").read())
            # 兼容旧格式 {"items": [...]} → 扁平数组
            if isinstance(data, dict) and "items" in data:
                return data["items"]
            if isinstance(data, list):
                return data
        except:
            pass
    return []


def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class Handler(BaseHTTPRequestHandler):

    def _send(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_GET(self):
        # nginx 已将 /api/ 前缀剥离，这里匹配 /bookmark
        if self.path == "/bookmark":
            self._send(200, load())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        # nginx 已将 /api/ 前缀剥离，这里匹配 /bookmark
        if self.path != "/bookmark":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except:
            self._send(400, {"error": "invalid JSON"})
            return

        action = payload.get("action", "")
        full_name = payload.get("full_name", "")

        if not full_name:
            self._send(400, {"error": "missing full_name"})
            return

        bookmarks = load()
        existing = {b["full_name"]: b for b in bookmarks}

        if action == "remove":
            existing.pop(full_name, None)
            save(list(existing.values()))
            self._send(200, {"status": "ok", "action": "removed"})
        elif action == "add":
            bookmark = payload.get("bookmark", {})
            if bookmark:
                bookmark["full_name"] = full_name
                existing[full_name] = bookmark
                save(list(existing.values()))
            self._send(200, {"status": "ok", "action": "added"})
        else:
            self._send(400, {"error": f"unknown action: {action}"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[bookmark-api] {args[0]} {args[1]} {args[2]}")


if __name__ == "__main__":
    port = 5002
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"✅ Bookmark API 运行在 http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️ 服务停止")
        server.server_close()
