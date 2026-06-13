#!/usr/bin/env python3
"""每日更新：GitHub 数据抓取 + 页面生成"""
import subprocess
from pathlib import Path

BASE = Path(__file__).parent

print("=" * 45)
print("  🤖 AI 日报 · 每日更新")
print("=" * 45)

# Step 1: Fetch GitHub projects
print("\n--- 🔥 GitHub 项目 ---")
subprocess.run(["python", str(BASE / "fetch_github_projects.py")])

# Step 2: 找最新的新闻 JSON 文件，生成完整页面
news_files = sorted(BASE.glob("news_*.json"))
if news_files:
    latest = news_files[-1]
    print(f"\n--- 🔨 生成页面（{latest.name}）---")
    subprocess.run(["python", str(BASE / "update_ai_daily.py"), str(latest)])
else:
    print("\n❌ 未找到新闻数据，跳过页面生成")
    print("  请先放置 news_YYYY-MM-DD.json 文件")
