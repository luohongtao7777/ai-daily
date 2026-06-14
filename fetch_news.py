#!/usr/bin/env python3
"""获取今日 AI 新闻 — 通过 Tavily API → 生成 news_YYYY-MM-DD.json"""
import json
import urllib.request
import urllib.error
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).parent
API_KEY = "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"
API_URL = "https://api.tavily.com"
CST = timezone(timedelta(hours=8))

# 优质新闻源（排除社交媒体）
NEWS_DOMAINS = [
    "reuters.com", "techcrunch.com", "theverge.com", "arstechnica.com",
    "venturebeat.com", "bloomberg.com", "wired.com", "nature.com",
    "technologyreview.com", "theinformation.com", "axios.com",
    "bbc.com", "bbc.co.uk", "cnn.com", "wsj.com", "nytimes.com",
    "ft.com", "economist.com", "apnews.com", "npr.org",
    "zdnet.com", "infoworld.com", "computerworld.com",
    "blog.google", "openai.com", "anthropic.com", "ibm.com",
    "microsoft.com", "meta.com", "about.google",
    # 中文
    "36kr.com", "huxiu.com", "jiqizhixin.com", "leiphone.com",
    "caixin.com", "yicai.com", "thepaper.cn",
    "news.cn", "xinhuanet.com", "people.com.cn",
    "bbc.com/zhongwen", "bbcchinese.com",
]

EXCLUDE_DOMAINS = [
    "reddit.com", "x.com", "twitter.com", "youtube.com", "youtu.be",
    "tiktok.com", "instagram.com", "facebook.com", "linkedin.com",
    "pinterest.com", "medium.com", "substack.com",
    "github.com", "gitlab.com", "stackoverflow.com",
    "amazon.com", "amazonaws.com",
    # 文件托管
    "cdn.", "pdf.", "docs.google.com",
]

# 中文分类关键词
CATEGORIES = {
    "model": "模型发布", "launch": "模型发布", "release": "模型发布",
    "fund": "融资", "raise": "融资", "invest": "融资", "round": "融资",
    "chip": "芯片", "hardware": "芯片", "semiconductor": "芯片", "nvidia": "芯片",
    "robot": "具身智能", "humanoid": "具身智能", "robotics": "具身智能",
    "drug": "AI+科学", "sci": "AI+科学", "health": "AI+科学",
    "med": "AI+科学", "protein": "AI+科学", "research": "AI+科学",
    "regulation": "政策", "policy": "政策", "law": "政策",
    "china": "动态", "openai": "动态", "google": "动态",
    "ant": "动态", "meta": "动态", "apple": "动态",
    "trend": "行业趋势", "report": "行业趋势", "prediction": "行业趋势",
    "market": "行业趋势", "economy": "行业趋势",
    "security": "安全", "safety": "安全", "alignment": "安全",
    "open source": "开源", "opensource": "开源",
    "coding": "开发工具", "code": "开发工具", "developer": "开发工具",
}


def tavily_search(query: str, max_results: int = 8) -> list[dict]:
    """调用 Tavily Search API"""
    data = json.dumps({
        "api_key": API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": max_results,
        "include_domains": NEWS_DOMAINS,
        "exclude_domains": EXCLUDE_DOMAINS,
    }).encode()
    req = urllib.request.Request(
        f"{API_URL}/search",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read()).get("results", [])
    except Exception as e:
        print(f"  ⚠️ Tavily 搜索失败: {e}", file=sys.stderr)
        return []


def tavily_extract(urls: list[str]) -> dict[str, str]:
    """调用 Tavily Extract API 获取文章正文"""
    if not urls:
        return {}
    data = json.dumps({
        "api_key": API_KEY,
        "urls": urls,
        "extract_depth": "basic",
    }).encode()
    req = urllib.request.Request(
        f"{API_URL}/extract",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            results = json.loads(resp.read()).get("results", [])
            return {r.get("url", ""): r.get("raw_content", "") for r in results}
    except Exception as e:
        print(f"  ⚠️ Tavily 提取失败: {e}", file=sys.stderr)
        return {}


def guess_category(title: str, content: str) -> str:
    """根据标题和内容推测分类"""
    lower = (title + " " + content[:500]).lower()
    for keyword, cat in CATEGORIES.items():
        if keyword in lower:
            return cat
    return "综合"


def guess_source(url: str, result_source: str) -> str:
    """推测来源名称"""
    if result_source and result_source.lower() not in ("unknown", ""):
        return result_source
    domain = url.split("/")[2] if "//" in url else url
    domain_map = {
        "reuters.com": "Reuters", "techcrunch.com": "TechCrunch",
        "theverge.com": "The Verge", "arstechnica.com": "Ars Technica",
        "venturebeat.com": "VentureBeat", "bloomberg.com": "Bloomberg",
        "wired.com": "Wired", "nature.com": "Nature",
        "technologyreview.com": "MIT Tech Review",
        "theinformation.com": "The Information",
        "axios.com": "Axios", "bbc.com": "BBC", "bbc.co.uk": "BBC",
        "cnn.com": "CNN", "wsj.com": "WSJ", "nytimes.com": "NYT",
        "ft.com": "Financial Times", "economist.com": "The Economist",
        "apnews.com": "AP News", "npr.org": "NPR",
        "zdnet.com": "ZDNet", "infoworld.com": "InfoWorld",
        "36kr.com": "36氪", "huxiu.com": "虎嗅",
        "jiqizhixin.com": "机器之心", "leiphone.com": "雷锋网",
        "caixin.com": "财新", "yicai.com": "第一财经",
        "thepaper.cn": "澎湃新闻", "people.com.cn": "人民网",
        "blog.google": "Google Blog", "openai.com": "OpenAI",
        "anthropic.com": "Anthropic", "ibm.com": "IBM",
        "microsoft.com": "Microsoft",
    }
    for d, name in domain_map.items():
        if d in domain:
            return name
    return domain.replace("www.", "").split(".")[0].capitalize()


def is_low_quality(item: dict) -> bool:
    """过滤低质量条目"""
    title = (item.get("title") or "").lower()
    # 排除太短/无意义标题
    if len(title.strip()) < 10:
        return True
    # 排除文件格式
    if any(ext in title for ext in [".pdf", ".docx", ".pptx"]):
        return True
    # 排除明显非新闻
    low_quality_keywords = [
        "apply now", "internship", "deadline", "register",
        "sponsor", "promotion", "discount", "coupon",
        "weather", "horoscope", "crossword", "recipe",
    ]
    if any(kw in title for kw in low_quality_keywords):
        return True
    return False


def deduplicate(items: list[dict]) -> list[dict]:
    """去重（同一URL只保留一个）"""
    seen_urls = set()
    result = []
    for item in items:
        url = item.get("url", "")
        clean = url.split("?")[0].split("#")[0]
        # 也去重相似标题
        title = (item.get("title") or "").strip().lower()[:40]
        key = clean or title
        if key and key not in seen_urls:
            seen_urls.add(key)
            result.append(item)
    return result


def main():
    today = datetime.now(CST)
    date_str = today.strftime("%Y-%m-%d")
    out_file = BASE / f"news_{date_str}.json"

    if out_file.exists():
        print(f"  ✅ {out_file.name} 已存在，跳过")
        return

    print(f"\n--- 📰 获取 {date_str} AI 新闻 ---")

    # 针对性的搜索查询（覆盖不同子领域）
    queries = [
        # 模型发布与 AI 公司动态
        "AI model launch announcement 2026",
        "OpenAI Anthropic Google AI news 2026",
        # 融资与商业
        "AI startup funding investment 2026",
        # 芯片与硬件
        "AI chip semiconductor NVIDIA 2026",
        # 具身智能与机器人
        "AI robotics humanoid robot 2026",
        # 行业趋势与报告
        "AI industry report prediction 2026",
        # 中文新闻
        "人工智能 AI 新闻 2026",
    ]

    all_results = []
    for q in queries:
        print(f"  搜索: {q}...", end=" ", flush=True)
        results = tavily_search(q, max_results=5)
        print(f"→ {len(results)} 条")
        all_results.extend(results)
        time.sleep(0.3)

    # 去重
    all_results = deduplicate(all_results)
    print(f"  去重后共 {len(all_results)} 条")

    # 过滤低质量
    all_results = [r for r in all_results if not is_low_quality(r)]
    print(f"  过滤低质量后 {len(all_results)} 条")

    if not all_results:
        print("  ⚠️ 未获取到足够质量的新闻，跳过本次")
        return

    # 按相关性/新鲜度排序（Tavily 已排序），取最多 8 条
    all_results = all_results[:8]

    # 提取正文
    urls = [r["url"] for r in all_results if r.get("url")]
    print(f"  提取 {len(urls)} 篇文章正文...")
    contents = tavily_extract(urls)
    time.sleep(1)

    # 组装新闻条目
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_names[today.weekday()]

    items = []
    for r in all_results:
        url = r.get("url", "")
        content = contents.get(url, "") or r.get("content", "")
        content = content[:8000] if content else ""

        # 摘要：优先用 Tavily 的 content，太短则从正文截取
        summary = (r.get("content") or r.get("description") or "")[:300]
        if len(summary) < 50 and content:
            paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
            summary = (paragraphs[0] if paragraphs else "")[:300]

        item = {
            "title": (r.get("title") or "").strip(),
            "url": url,
            "source": guess_source(url, r.get("source", "")),
            "category": guess_category(r.get("title", ""), content),
            "summary": summary,
            "full_content": content,
            "terms": {},
            "impact": "",
        }
        if item["title"]:
            items.append(item)

    if not items:
        print("  ❌ 生成的新闻条目为空，跳过")
        return

    # 保存
    news_data = {
        "date": date_str,
        "weekday": weekday,
        "items": items,
    }
    out_file.write_text(json.dumps(news_data, ensure_ascii=False, indent=2), "utf-8")
    print(f"  ✅ 已保存 {out_file.name}（{len(items)} 条新闻）")

    for i, it in enumerate(items, 1):
        print(f"  {i:2d}. [{it['category']}] {it['title'][:60]}")


if __name__ == "__main__":
    main()
