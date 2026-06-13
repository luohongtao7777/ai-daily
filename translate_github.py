#!/usr/bin/env python3
"""检查 github_projects.json 中缺少中文翻译的项目，输出报告"""
import json
from pathlib import Path

BASE = Path(__file__).parent
DATA_FILE = BASE / "github_projects.json"

if not DATA_FILE.exists():
    print("❌ github_projects.json 不存在")
    exit(0)

data = json.loads(DATA_FILE.read_text("utf-8"))
items = data.get("items", [])

needed = []
for i, p in enumerate(items):
    fn = p["full_name"]
    needs_readme = not p.get("_readme_cn") and p.get("_readme_raw", "").strip()
    needs_summary = not p.get("_summary_cn") and p.get("description", "").strip()
    if needs_readme or needs_summary:
        needed.append({
            "index": i,
            "full_name": fn,
            "description": p.get("description", ""),
            "needs_readme": needs_readme,
            "needs_summary": needs_summary,
            "readme_len": len(p.get("_readme_raw", "")),
        })

if not needed:
    print("✅ 所有项目已有中文翻译，无需处理")
    exit(0)

print(f"⚠️  发现 {len(needed)} 个项目缺少中文翻译：\n")
for n in needed:
    parts = []
    if n["needs_readme"]: parts.append(f"📖 README ({n['readme_len']} 字符)")
    if n["needs_summary"]: parts.append("📝 摘要")
    print(f"  [{n['index']}] {n['full_name']}")
    print(f"      缺失: {'、'.join(parts)}")
    print(f"      描述: {n['description'][:100]}")
    print()

# 也输出 JSON 供脚本消费
print("---JSON_START---")
print(json.dumps({"need_translation": True, "items": needed}, ensure_ascii=False))
print("---JSON_END---")
