#!/usr/bin/env python3
"""
同步 GitHub 收藏项目到 Obsidian
从服务器获取书签数据，写入 Obsidian 仓库

使用方法：
  python sync_bookmarks_to_obsidian.py          # 正常同步
  python sync_bookmarks_to_obsidian.py --force  # 强制全部重新同步
"""
import json
import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# ========== 配置 ==========
OBSIDIAN_VAULT = Path(r"C:\obsidian\7777")
BOOKMARK_DIR = "学习笔记/GitHub收藏"
BOOKMARK_API = "http://82.156.80.178/api/bookmarks"
TRACKING_FILE = Path(__file__).parent / ".synced_bookmarks.json"


def fetch_bookmarks():
    """从服务器获取书签列表"""
    result = subprocess.run(
        ["curl", "-s", BOOKMARK_API],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode != 0:
        print(f"❌ 无法连接服务器: {result.stderr}")
        return None
    try:
        data = json.loads(result.stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        print(f"❌ 解析服务器响应失败")
        return None


def get_synced():
    """获取已同步的 full_name 列表"""
    if TRACKING_FILE.exists():
        try:
            return set(json.loads(TRACKING_FILE.read_text("utf-8")))
        except Exception:
            return set()
    return set()


def save_synced(synced_set):
    """保存已同步列表"""
    TRACKING_FILE.write_text(
        json.dumps(sorted(synced_set), ensure_ascii=False, indent=2),
        "utf-8"
    )


def classify_project(project):
    """根据项目内容判断分类"""
    name = (project.get("name", "") + " " + 
            project.get("summary", "") + " " +
            project.get("description", "")).lower()
    
    if any(kw in name for kw in ["claude", "anthropic"]):
        return "Claude 生态"
    if any(kw in name for kw in ["hermes", "openclaw"]):
        return "Hermes/OpenClaw"
    if any(kw in name for kw in ["codex", "opencode"]):
        return "编码工具"
    if any(kw in name for kw in ["mcp", "protocol"]):
        return "MCP/协议"
    if any(kw in name for kw in ["agent", "framework", "autonomous", "swarm"]):
        return "Agent 框架"
    if any(kw in name for kw in ["memory", "context"]):
        return "记忆/上下文"
    if any(kw in name for kw in ["skills", "skill"]):
        return "技能/插件"
    if any(kw in name for kw in ["design", "ui"]):
        return "设计工具"
    return "其他"


def write_project_note(project, category):
    """为单个项目写 Obsidian 笔记"""
    name = project.get("name", "unknown")
    full_name = project.get("full_name", "")
    url = project.get("url", "")
    stars = project.get("stars", 0)
    lang = project.get("language", "N/A")
    summary = project.get("summary", project.get("description", "无描述"))
    impact = project.get("impact", "")
    terms = project.get("terms", {})
    bookmarked_at = project.get("bookmarked_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

    # 文件名：清理非法字符
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)[:60]
    file_path = OBSIDIAN_VAULT / BOOKMARK_DIR / f"{safe_name}.md"

    terms_block = ""
    if terms:
        term_lines = []
        for k, v in terms.items():
            term_lines.append(f"  - **{k}**：{v}")
        terms_block = "\n".join(term_lines)

    content = f"""---
收藏日期: {bookmarked_at[:10]}
分类: {category}
⭐ Stars: {stars}
语言: {lang}
全名: {full_name}
---

# {name}

> {url}

## 项目简介

{summary}

## 基本信息

| 属性 | 值 |
|------|-----|
| ⭐ Stars | {stars} |
| 语言 | {lang} |
| 全名 | `{full_name}` |
| 收藏时间 | {bookmarked_at[:19]} |

## 影响/价值

{impact}
"""

    if terms_block:
        content += f"""
## 专业术语

{terms_block}
"""

    content += """
---

*由 AI 日报自动同步*
"""

    # 写入文件
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, "utf-8")
    print(f"  ✅ {safe_name}.md")
    return True


def update_index(projects_list):
    """更新分类索引页"""
    # 按分类组织
    by_category = {}
    for p in projects_list:
        cat = classify_project(p)
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(p)

    index_path = OBSIDIAN_VAULT / BOOKMARK_DIR / "index.md"
    
    lines = ["# 📌 GitHub 项目收藏", "", f"共 {len(projects_list)} 个项目", "", "---", ""]
    
    for cat in sorted(by_category.keys()):
        items = by_category[cat]
        lines.append(f"## {cat}（{len(items)}）")
        lines.append("")
        for p in items:
            name = p.get("name", "?")
            stars = p.get("stars", 0)
            summary = (p.get("summary", "") or p.get("description", ""))[:80]
            link = p.get("url", "")
            # 用 Obsidian wiki 链接
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)[:60]
            lines.append(f"- [[{safe_name}]] ⭐{stars} — {summary}")
        lines.append("")
    
    lines.append("---")
    lines.append(f"*最后同步：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines), "utf-8")
    print(f"  📋 index.md ({len(projects_list)} 个项目)")


def main():
    print("=" * 50)
    print("  GitHub 收藏 → Obsidian 同步")
    print("=" * 50)

    force = "--force" in sys.argv

    # 获取已同步记录
    synced = get_synced()

    # 获取书签
    bookmarks = fetch_bookmarks()
    if bookmarks is None:
        print("❌ 无法获取书签，同步终止")
        return 1

    print(f"📦 服务器上有 {len(bookmarks)} 个书签")

    if not force:
        new_items = [b for b in bookmarks if b.get("full_name") not in synced]
    else:
        new_items = bookmarks

    # 也包含之前已同步但需要更新的
    all_items = bookmarks

    if not force:
        print(f"🆕 待同步新项目: {len(new_items)} 个")
        if not new_items:
            print("✅ 没有新收藏，跳过")
            return 0

    # 写入每个项目
    for project in all_items:
        cat = classify_project(project)
        write_project_note(project, cat)

    # 更新索引
    update_index(all_items)

    # 更新同步状态
    new_synced = set(b.get("full_name") for b in bookmarks)
    save_synced(new_synced)

    print(f"\n✅ 同步完成！已记录 {len(new_synced)} 个书签")
    print(f"📂 {OBSIDIAN_VAULT / BOOKMARK_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
