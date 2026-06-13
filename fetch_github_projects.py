#!/usr/bin/env python3
"""获取 GitHub 上 AI 智能体相关的涨星最快项目 + README 内容"""
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
import base64

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "github_projects.json"

SEARCH_QUERIES = [
    "claude-code+agent+created:>",
    "hermes-agent+OR+openclaw+created:>",
    "ai-coding-agent+OR+mcp-server+created:>",
]

POPULAR_QUERIES = [
    "claude-code+agent+stars:>10000",
    "ai-agent+framework+stars:>10000",
    "mcp-server+stars:>5000",
]

EXCLUDE = ["voltagent", "ultraworker", "garrytan/", "juliusbrussee",
           "safishamsi", "santifer/", "egonex-ai", "multica-ai", "esengine/"]


def search(q, per_page=15):
    r = subprocess.run(["curl", "-s", f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page={per_page}"],
                       capture_output=True, text=True, timeout=15)
    if r.returncode != 0: return []
    try: return json.loads(r.stdout).get("items", [])
    except: return []


def parse(item):
    return {
        "full_name": item["full_name"], "name": item["name"], "url": item["html_url"],
        "description": item.get("description","") or "", "stars": item["stargazers_count"],
        "forks": item["forks_count"], "language": item.get("language") or "N/A",
        "topics": item.get("topics",[]), "open_issues": item["open_issues_count"],
        "license": (item.get("license") or {}).get("spdx_id","") or "N/A",
        "created_at": (item.get("created_at") or "")[:10],
        "updated_at": (item.get("updated_at") or "")[:10],
    }


def fetch_readme(full_name):
    """获取 README 并解码"""
    r = subprocess.run(["curl", "-s", f"https://api.github.com/repos/{full_name}/readme"],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0: return ""
    try:
        data = json.loads(r.stdout)
        content = data.get("content", "")
        if content:
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")
            return decoded[:15000]  # 取前15000字符（覆盖大部分 README 全文）
    except:
        pass
    return ""


def main():
    print("=" * 50)
    print("  GitHub 涨星最快 AI 智能体项目")
    print("=" * 50)

    all_items = []
    cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    for q in SEARCH_QUERIES:
        items = search(f"{q}{cutoff}")
        all_items.extend(parse(i) for i in items)
        time.sleep(0.3)

    for q in POPULAR_QUERIES:
        items = search(q)
        all_items.extend(parse(i) for i in items)
        time.sleep(0.3)

    # 去重 + 过滤
    seen = set()
    items = []
    for p in all_items:
        fn = p["full_name"]
        if fn in seen or any(x in fn.lower() for x in EXCLUDE):
            continue
        seen.add(fn)
        items.append(p)

    # 计算涨星速度（纯）
    for p in items:
        try:
            days = max((datetime.now() - datetime.strptime(p["created_at"], "%Y-%m-%d")).days, 1)
            p["_growth"] = round(p["stars"] / days, 1)
        except:
            p["_growth"] = 0

    items.sort(key=lambda p: -p["_growth"])
    items = items[:10]

    # 取 README
    print("\n📖 拉取 README…")
    for p in items:
        print(f"  {p['full_name']}... ", end="", flush=True)
        readme = fetch_readme(p["full_name"])
        if readme:
            p["_readme_raw"] = readme
            print(f"✅ {len(readme)} 字符")
        else:
            print("⏭️")
        time.sleep(0.3)

    # 格式化星星
    def fmt(n):
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1000: return f"{n//1000}K"
        return str(n)
    for p in items:
        p["_stars_fmt"] = fmt(p["stars"])

    # 保存（保留 _growth, _stars_fmt, _readme_raw 供后续翻译使用）
    DATA_FILE.write_text(json.dumps({
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(items),
        "items": items,
    }, ensure_ascii=False, indent=2), "utf-8")

    print(f"\n🏆 涨星最快 Top {len(items)}:")
    for i, p in enumerate(items, 1):
        print(f"  {i:2d}. ⭐{p['_stars_fmt']:>6s}  (+{p['_growth']:.0f}/天)  {p['full_name']}")
    print(f"\n✅ 已保存，含 README 内容")


if __name__ == "__main__":
    main()
