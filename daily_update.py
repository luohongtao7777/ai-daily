#!/usr/bin/env python3
"""每日更新：GitHub 数据抓取 + 书签同步 + 新闻清理 + 页面生成"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

BASE = Path(__file__).parent

print("=" * 45)
print("  🤖 AI 日报 · 每日更新")
print("=" * 45)

# Step 1: Fetch GitHub projects
print("\n--- 🔥 GitHub 项目 ---")
subprocess.run(["python", str(BASE / "fetch_github_projects.py")])

# Step 1.5: 翻译检查 — 输出 JSON 标记给 agent 消费
print("\n--- 🌐 翻译检查 ---")
result = subprocess.run(
    ["python", str(BASE / "translate_github.py")],
    capture_output=True, text=True
)
print(result.stdout.strip())
if result.stdout and "---JSON_START---" in result.stdout:
    json_part = result.stdout.split("---JSON_START---")[1].split("---JSON_END---")[0].strip()
    tmp = BASE / ".translation_needed.json"
    tmp.write_text(json_part, "utf-8")
    print(f"  详情写入 {tmp}")
else:
    tmp = BASE / ".translation_needed.json"
    if tmp.exists(): tmp.unlink()

# Step 2: 从服务器同步书签
print("\n--- ⭐ 同步书签 ---")
try:
    subprocess.run([
        "scp",
        "ubuntu@82.156.80.178:/home/ubuntu/bookmarks/bookmarks.json",
        str(BASE / "bookmarks.json")
    ], capture_output=True, text=True, timeout=15)
    bm_file = BASE / "bookmarks.json"
    if bm_file.exists():
        bm_data = json.loads(bm_file.read_text("utf-8"))
        if isinstance(bm_data, dict) and "items" in bm_data:
            count = len(bm_data["items"])
        elif isinstance(bm_data, list):
            count = len(bm_data)
        else:
            count = 0
        print(f"  ✅ 已同步 {count} 个书签")
except Exception as e:
    print(f"  ⚠️ 书签同步失败（首次运行无妨）: {e}")

# Step 3: 清理超过 5 天的 news_*.json
print("\n--- 🗑️ 清理旧新闻 ---")
cutoff = datetime.now() - timedelta(days=5)
for f in sorted(BASE.glob("news_*.json")):
    try:
        # 文件名: news_YYYY-MM-DD.json
        date_str = f.stem.replace("news_", "")
        fdate = datetime.strptime(date_str, "%Y-%m-%d")
        if fdate < cutoff:
            f.unlink()
            print(f"  🗑️ 已删除 {f.name}")
    except:
        pass

# Step 4: 生成页面
print("\n--- 🔨 生成页面 ---")
news_files = sorted(BASE.glob("news_*.json"))
if news_files:
    latest = news_files[-1]
    print(f"  使用 {latest.name}")
    subprocess.run(["python", str(BASE / "update_ai_daily.py"), str(latest)])
else:
    print("  ❌ 未找到新闻数据，跳过页面生成")
    print("  请先放置 news_YYYY-MM-DD.json 文件")

# Step 5: 书签同步到 Obsidian
print("\n--- 📝 书签 → Obsidian ---")
try:
    subprocess.run(["python", str(BASE / "update_ai_daily.py"), "--sync-bookmarks"], capture_output=True, text=True)
    print("  ✅ Obsidian 书签已更新")
except Exception as e:
    print(f"  ⚠️ Obsidian 同步失败: {e}")
