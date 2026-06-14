#!/usr/bin/env python3
"""AI 日报更新脚本 — 新闻 + GitHub 项目一体化生成"""
import json, sys, re, subprocess
from datetime import datetime
from pathlib import Path

# ========== 配置 ==========
HTML_PATH = Path(__file__).parent / "index.html"
OBSIDIAN_VAULT = Path("C:/obsidian/7777/学习笔记/AI日报")
SERVER = "ubuntu@82.156.80.178"
REMOTE_PATH = "/var/www/html/ai-daily/index.html"
BOOKMARKS_PATH = Path(__file__).parent / "bookmarks.json"
MAX_DAYS = 5
ARTICLES_MARKER = "<!--=ARTICLES_MARKER=-->"
GITHUB_PATH = Path(__file__).parent / "github_projects.json"
WEEKDAY_NAMES = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]

def _escape(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;")

def _domain(url):
    return re.sub(r"https?://(www\.)?","",url).split("/")[0]

def load_news():
    if len(sys.argv)>1:
        with open(sys.argv[1],encoding="utf-8") as f: return json.load(f)
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else None

def load_github(date=None):
    """加载 GitHub 数据，优先按日期读取快照"""
    base_dir = GITHUB_PATH.parent
    if date:
        dated = base_dir / f"gh_{date}.json"
        if dated.exists():
            return json.loads(dated.read_text("utf-8"))
    if GITHUB_PATH.exists():
        return json.loads(GITHUB_PATH.read_text("utf-8"))
    return None

def get_html():
    if HTML_PATH.exists(): return HTML_PATH.read_text("utf-8")
    base = Path(__file__).parent / "index.base.html"
    if base.exists(): return base.read_text("utf-8")
    return None

# ===== 新闻生成 =====
def build_day(date, weekday, items):
    dd = f"{date[:4]}年{int(date[5:7])}月{int(date[8:])}日"
    L = [f'<section class="day-section" id="day-{date}">',
         f'  <div class="day-header">',
         f'    <span class="date">{dd}</span>',
         f'    <span class="weekday">{weekday}</span>',
         f'    <span class="update-badge">📡 {len(items)} 条资讯</span>',
         f'  </div>']
    for i, it in enumerate(items):
        L.append(f'  <div class="news-card" onclick="showArticle(\'article-{date}-{i}\')">')
        L.append(f'    <div class="source-row">')
        L.append(f'      <span class="source-badge">{it.get("source","综合")}</span>')
        if it.get("category"): L.append(f'      <span class="category-tag">{it["category"]}</span>')
        if it.get("url"): L.append(f'      <span class="source-url">{_domain(it["url"])}</span>')
        L.append(f'    </div>')
        L.append(f'    <h3 class="card-title">{it.get("title","")}</h3>')
        L.append(f'    <div class="card-preview">{_escape(it.get("summary",""))}</div>')
        L.append(f'  </div>')
    L.append('</section>')
    return "\n".join(L)

def build_articles(date, items):
    L = [f'<div id="articles-{date}" class="article-group">']
    for i, it in enumerate(items):
        aid = f"article-{date}-{i}"
        L.append(f'  <div id="{aid}" class="article-item">')
        L.append(f'    <div class="article-meta">')
        L.append(f'      <span class="source-badge">{it.get("source","综合")}</span>')
        if it.get("category"): L.append(f'      <span class="category-tag">{it["category"]}</span>')
        if it.get("url"): L.append(f'      <span class="source-url">{_domain(it["url"])}</span>')
        L.append(f'      <span class="article-date">{date}</span>')
        L.append(f'    </div>')
        title = it.get("title","")
        L.append(f'    <h2 class="article-title">{_escape(title)}</h2>')
        img = it.get("image_url","")
        if img: L.append(f'    <img class="news-img" src="{_escape(img)}" alt="{_escape(title)}" loading="lazy">')
        summary = it.get("full_content") or it.get("summary","")
        L.append(f'    <div class="content">')
        for p in (summary.split("\n\n") if "\n\n" in summary else [summary]):
            if p.strip(): L.append(f'      <p>{_escape(p.strip())}</p>')
        L.append(f'    </div>')
        if it.get("terms"):
            L.append(f'    <div class="terms-section">')
            for k,v in it["terms"].items(): L.append(f'      <span class="glossary-term">{_escape(k)}<span class="term-tip">{_escape(v)}</span></span>')
            L.append(f'    </div>')
        if it.get("impact"): L.append(f'    <div class="impact"><strong>💡 影响解读：</strong>{_escape(it["impact"])}</div>')
        if it.get("url") and it.get("source"): L.append(f'    <div class="source-ref">📎 原文：{_escape(it["source"])}（{_domain(it["url"])}，英文）</div>')
        L.append(f'  </div>')
    L.append(f'</div>')
    L.append(f'<!-- /article-group:{date} -->')
    return "\n".join(L)

def build_nav(days):
    """生成导航链接，第一个（最新日期）默认 active"""
    links = []
    for i, (d, w) in enumerate(days):
        cls = ' class="active"' if i == 0 else ""
        links.append(f'  <a href="javascript:void(0)" onclick="scrollToDay(\'{d}\')" data-date="{d}"{cls}>{d[5:]} {w}</a>')
    return "\n".join(links)

def extract_days(html):
    return re.findall(r'id="day-(\d{4}-\d{2}-\d{2})"', html)

def prune_old(html):
    days = extract_days(html)
    if len(days) <= MAX_DAYS: return html, False
    for d in sorted(set(days))[:len(set(days))-MAX_DAYS]:
        html = re.sub(rf'<section class="day-section" id="day-{re.escape(d)}">.*?</section>', "", html, flags=re.DOTALL)
        html = re.sub(rf'<div id="articles-{re.escape(d)}" class="article-group">.*?</div><!-- /article-group:{re.escape(d)} -->', "", html, flags=re.DOTALL)
    print(f"  清理了旧记录（保留最近 {MAX_DAYS} 天）")
    return html, True

# ===== GitHub 生成 =====
def clean_readme(t):
    if not t: return ""
    for p in [r'<[^>]+>', r'!\[.*?\]\(.*?\)', r'\[\]\([^)]*\)']: t = re.sub(p, '', t)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'^#{1,6}\s+', '', t, flags=re.MULTILINE)
    for c in ['**','__','*','_','`']: t = t.replace(c, '')
    t = re.sub(r'\n[-_]{3,}\n', '\n', t)
    t = re.sub(r'^>\s*', '', t, flags=re.MULTILINE)
    t = re.sub(r'^\s*[-*+]\s+', '• ', t, flags=re.MULTILINE)
    t = re.sub(r'^\s*\d+\.\s+', '  ', t, flags=re.MULTILINE)
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = '\n'.join(l.rstrip() for l in t.split('\n'))
    return t.strip()

def gh_cards(items):
    cards = []
    for i,p in enumerate(items):
        lang = f'<span class="gh-lang">{p["language"]}</span>' if p.get("language") else ""
        desc = (p.get("_summary_cn") or p.get("summary") or p.get("description") or "")[:120]
        cards.append(f'''  <div class="gh-card" onclick="showGhProject({i})">
    <div class="gh-card-top">
      <div class="gh-card-title">{p["name"]}<span class="gh-owner">{p["full_name"]}</span></div>
      <button class="bookmark-btn" onclick="event.stopPropagation(); toggleBookmark({i})" id="bm-{i}" data-full='{p["full_name"]}'>☆</button>
    </div>
    <div class="gh-card-meta">
      <span class="gh-stars">{p["stars"]}</span> {lang} <span class="gh-forks">{p["forks"]}</span>
    </div>
    <div class="gh-card-desc">{desc}</div>
  </div>''')
    return "\n".join(cards)

def gh_details(items):
    def _one(p,i):
        terms = "".join(f'<span class="glossary-term">{k}<span class="term-tip">{v}</span></span>' for k,v in (p.get("terms") or {}).items())
        imp = f'<div class="impact"><strong>💡 影响解读：</strong>{p["impact"]}</div>' if p.get("impact") else ""
        rc = p.get("_readme_cn") or p.get("_readme_raw") or ""
        rc = clean_readme(rc)
        rd = f'<div class="readme-content"><h4>📖 项目介绍</h4><div class="readme-text">{_escape(rc)}</div></div>' if len(rc)>=30 else ""
        return f'''  <div id="gh-detail-{i}" class="article-item">
    <div class="gh-detail-header">
      <span class="source-badge">{p.get("language","")}</span>
      <span class="gh-owner">{p["full_name"]}</span>
    </div>
    <h2 class="article-title">{p["name"]}</h2>
    <div class="gh-detail-stats">
      <span>⭐ <strong>{p["stars"]}</strong> stars</span>
      <span>⑂ <strong>{p["forks"]}</strong> forks</span>
      <span>📋 <strong>{p.get("open_issues",0)}</strong> issues</span>
    </div>
    <div class="content"><p>{p.get("_summary_cn") or p.get("summary",p.get("description",""))}</p></div>
    {rd}{terms or ""}{imp}
    <div class="source-ref">🔗 <a href="{p["url"]}" target="_blank" style="color:var(--accent);text-decoration:none;">{p["full_name"]}</a></div>
  </div>'''
    return "\n".join(_one(p,i) for i,p in enumerate(items))

GH_CSS = """
  .tab-bar { display:flex; background:#fff; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:99; box-shadow:0 1px 3px rgba(0,0,0,0.04); }
  .tab-bar .tab { flex:1; text-align:center; padding:12px 8px; font-size:14px; font-weight:600; color:var(--muted); cursor:pointer; transition:all .25s ease; border-bottom:2px solid transparent; user-select:none; touch-action:manipulation; }
  .tab-bar .tab.active { color:var(--accent); border-bottom-color:var(--accent); background:#f8faff; }
  .tab-bar .tab:active { background:#f0f4ff; }
  .tab-pane { display:none; }
  .tab-pane.active { display:block; }
  .github-header { display:flex; align-items:center; justify-content:space-between; padding:16px 16px 8px; font-size:15px; font-weight:600; color:var(--text); }
  .github-header .update-time { font-size:11px; font-weight:400; color:var(--muted); }
  .github-section { padding:0 16px 16px; }
  .gh-card { background:var(--card-bg); border-radius:12px; padding:14px 16px; margin-bottom:10px; box-shadow:var(--shadow); cursor:pointer; transition:transform .15s ease,box-shadow .15s ease; border:1px solid var(--border); position:relative; }
  .gh-card:active { transform:scale(.98); }
  .gh-card-top { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; }
  .gh-card-title { font-size:15px; font-weight:600; color:var(--accent); line-height:1.3; flex:1; }
  .gh-card-title .gh-owner { font-size:12px; font-weight:400; color:var(--muted); display:block; margin-top:1px; }
  .gh-stars { display:flex; align-items:center; gap:2px; font-size:13px; font-weight:600; color:var(--text); white-space:nowrap; }
  .gh-stars::before { content:"⭐"; font-size:12px; }
  .gh-card-desc { font-size:13px; color:var(--text-secondary); line-height:1.6; margin-top:6px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .gh-card-meta { display:flex; align-items:center; gap:8px; margin-top:8px; flex-wrap:wrap; }
  .gh-lang { font-size:11px; padding:2px 8px; border-radius:4px; background:#e8f5e9; color:#2e7d32; }
  .gh-forks { font-size:11px; color:var(--muted); }
  .gh-forks::before { content:"⑂ "; }
  .bookmark-btn { cursor:pointer; background:none; border:none; font-size:20px; line-height:1; padding:4px; transition:transform .2s ease; touch-action:manipulation; flex-shrink:0; }
  .bookmark-btn:active { transform:scale(1.3); }
  .bookmark-btn.active { animation:bookmark-pop .3s ease; }
  @keyframes bookmark-pop { 0%{transform:scale(1)} 50%{transform:scale(1.4)} 100%{transform:scale(1)} }
  .gh-detail-header { display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }
  .gh-detail-header .gh-owner { font-size:13px; color:var(--muted); }
  .gh-detail-stats { display:flex; gap:16px; margin-bottom:14px; padding-bottom:14px; border-bottom:1px solid var(--border); }
  .gh-detail-stats span { font-size:13px; color:var(--text-secondary); }
  .gh-detail-stats strong { color:var(--text); font-weight:600; }
  .readme-content { margin-top:16px; }
  .readme-content h4 { font-size:15px; margin-bottom:8px; }
  .readme-text { font-size:13px; line-height:1.7; color:var(--text-secondary); max-height:400px; overflow-y:auto; padding:10px 12px; background:#f8fafc; border-radius:8px; border:1px solid var(--border); }
"""

def inject_github(html, gh_data):
    items = (gh_data.get("items") or [])[:10]
    if not items: return html
    # 已有 ghData （新版页面）时跳过全部注入，由 ghData 机制管理
    if '// GH_DATA_START' in html:
        return html

    # 首次注入：页面还没有 tab-github
    if 'id="tab-github"' not in html:
        html = html.replace("</style>", GH_CSS + "\n</style>")

        # 1. tab-bar 放在 tab-news 前面
        tn = html.find('id="tab-news"')
        if tn >= 0:
            start = html.rfind('<div', 0, tn)
            if start >= 0:
                tb = '<div class="tab-bar" onclick="return handleTabClick(event)" ontouchstart="return handleTabClick(event)">\n  <span class="tab active" data-tab="news">📰 AI资讯</span>\n  <span class="tab" data-tab="github">🔥 热门项目</span>\n</div>\n'
                html = html[:start] + tb + html[start:]

        # 2. tab-github 放在 tab-news 闭合之后（仅含卡片列表，不含详情）
        ut = gh_data.get("updated_at", "")
        gh_tab = (
            '<div id="tab-github" class="tab-pane">\n'
            '  <div class="github-header">\n'
            f'    <span>🔥 AI 智能体热门项目</span>\n'
            f'    <span class="update-time">更新于 {ut}</span>\n'
            '  </div>\n'
            f'  <div class="github-section" id="github-cards">\n{gh_cards(items)}\n  </div>\n'
            '</div>\n'
        )
        # 通过结束标记找到 tab-news 的闭合位置
        end_marker = '<!-- end tab-news -->'
        tn_end = html.find(end_marker)
        if tn_end >= 0:
            # tab-github 插入到 marker 之后，不破坏 marker 与 </div> 的紧邻关系
            html = html.replace(end_marker, end_marker + '\n' + gh_tab + '\n')

        # 3. gh-detail 放入共享 detail-view（在 detail-back 元素后面）
        # 找实际的 <div class="detail-back" 元素（不是 CSS 中的 .detail-back）
        dvb = html.find('class="detail-back" onclick')
        if dvb >= 0:
            # 找到该 div 的闭合 </div>
            dve = html.find('</div>', dvb)
            if dve >= 0:
                html = html[:dve+6] + '\n' + gh_details(items) + html[dve+6:]

        # 4. toast
        be = html.find('</body>')
        if be >= 0:
            html = html[:be] + '\n<div class="toast" id="toast"></div>\n' + html[be:]

    # JS 注入（每次运行都更新数据）—— 已废弃 ghProjects 原地替换，
    # 因为 ghData 机制会设置正确的 ghProjects。只在首次注入完整 JS。
    gj = json.dumps(items, ensure_ascii=False).replace('</', '<\\/')
    idx = html.find('var ghProjects = ')
    if idx >= 0:
        # 仅在不含 GH_DATA_START（旧版页面）时做替换
        if '// GH_DATA_START' not in html:
            end = html.find('];', idx)
            if end >= 0:
                html = html[:idx] + f'var ghProjects = {gj};' + html[end+2:]
    else:
        js = (
            'function handleTabClick(e) {\n'
            "  var t=e.target; while(t&&!t.dataset.tab) t=t.parentNode; if(!t) return false;\n"
            "  var n=t.dataset.tab;\n"
            "  document.querySelectorAll('.tab-bar .tab').forEach(function(x){x.classList.remove('active');});\n"
            "  document.querySelectorAll('.tab-pane').forEach(function(x){x.classList.remove('active');});\n"
            "  t.classList.add('active'); var p=document.getElementById('tab-'+n); if(p) p.classList.add('active');\n"
            '  return false;\n'
            '}\n'
            'var bookmarked={};\n'
            "try{var s=localStorage.getItem('gh_bookmarks');if(s)bookmarked=JSON.parse(s);}catch(e){}\n"
            'function toggleBookmark(idx){\n'
            "  var btn=document.getElementById('bm-'+idx); if(!btn) return;\n"
            '  var fn=btn.dataset.full, p=ghProjects[idx]; if(!p) return;\n'
            "  if(bookmarked[fn]){\n"
            "    delete bookmarked[fn];\n"
            "    btn.textContent='\\u2606';btn.classList.remove('active');showToast('\\u5df2\\u53d6\\u6d88\\u6536\\u85cf');\n"
            "    var x=new XMLHttpRequest();x.open('POST','/api/bookmark',true);x.setRequestHeader('Content-Type','application/json');x.send(JSON.stringify({action:'remove',full_name:fn}));\n"
            '  }\n'
            '  else{\n'
            "    bookmarked[fn]={name:p.name,full_name:fn,url:p.url,stars:p.stars,language:p.language,summary:p.summary||p.description||'',bookmarked_at:new Date().toISOString()};\n"
            "    btn.textContent='\\u2605';btn.classList.add('active');showToast('\\u2705 \\u5df2\\u6536\\u85cf');\n"
            "    var x=new XMLHttpRequest();x.open('POST','/api/bookmark',true);x.setRequestHeader('Content-Type','application/json');x.send(JSON.stringify({action:'add',full_name:fn,bookmark:bookmarked[fn]}));\n"
            '  }\n'
            "  localStorage.setItem('gh_bookmarks',JSON.stringify(bookmarked));updateBookmarkUI();\n"
            '}\n'
            'function updateBookmarkUI(){document.querySelectorAll(\'.bookmark-btn\').forEach(function(b){var fn=b.dataset.full;b.textContent=bookmarked[fn]?\'\\u2605\':\'\\u2606\';b.classList.toggle(\'active\',!!bookmarked[fn]);});}\n'
            'function showToast(m){var t=document.getElementById(\'toast\');if(!t){t=document.createElement(\'div\');t.id=\'toast\';t.className=\'toast\';document.body.appendChild(t);}t.textContent=m;t.classList.add(\'show\');setTimeout(function(){t.classList.remove(\'show\');},2000);}\n'
            'var ghProjects=' + gj + ';\n'
            "if(typeof ghProjects==='string'){try{ghProjects=JSON.parse(ghProjects);}catch(e){ghProjects=[];}}\n"
            'function showGhProject(idx){\n'
            '  var p=ghProjects[idx]; if(!p) return;\n'
            "  document.querySelectorAll('.article-item').forEach(function(a){a.classList.remove('active');});\n"
            "  var t=document.getElementById('gh-detail-'+idx); if(t) t.classList.add('active');\n"
            "  savedScrollPos=window.scrollY;\n"
            "  document.querySelectorAll('.tab-pane').forEach(function(p){p.style.display='none';});\n"
            "  document.getElementById('list-view').style.display='none';\n"
            "  document.getElementById('detail-view').style.display='block';\n"
            "  document.getElementById('detail-view').scrollIntoView({block:'start'});\n"
            "  history.pushState({view:'ghdetail'},'');\n"
            '}\n'
            'setTimeout(updateBookmarkUI,100);'
        )
        ls = html.rfind('</script>', 0, html.find('</body>'))
        if ls >= 0:
            html = html[:ls] + js + html[ls:]
    return html

# ===== 书签嵌入 =====
def embed_bookmarks(html):
    """将服务端书签数据嵌入模板的 BOOKMARKS_JSON 标记位"""
    bm_dict = {}
    if BOOKMARKS_PATH.exists():
        try:
            bm = json.loads(BOOKMARKS_PATH.read_text("utf-8"))
            if isinstance(bm, dict) and "items" in bm:
                bm_dict = {b["full_name"]: b for b in bm["items"]}
            elif isinstance(bm, list):
                bm_dict = {b["full_name"]: b for b in bm}
        except:
            pass
    return html.replace("<!--=BOOKMARKS_JSON=-->", json.dumps(bm_dict, ensure_ascii=False))

# ===== 主流程 =====
def update_html(news, gh_data=None):
    html = get_html()
    if html is None: print("❌ 找不到 index.html"); return False
    html = embed_bookmarks(html)
    date, weekday, items = news["date"], news.get("weekday",""), news.get("items",[])
    nd = build_day(date, weekday, items)
    na = build_articles(date, items)
    if f'id="day-{date}"' in html:
        print(f"⚠️ {date} 已存在，跳过插入")
        if gh_data and gh_data.get("items"):
            updated = inject_github(html, gh_data)
            HTML_PATH.write_text(updated, "utf-8")
            print("✅ GitHub 数据已更新")
        return False
    is_first = "<!-- DAYS_PLACEHOLDER -->" in html
    if is_first:
        updated = html.replace("<!-- DAYS_PLACEHOLDER -->", f"\n{nd}\n")
        updated = updated.replace("<!-- DAY_NAV_PLACEHOLDER -->", build_nav([(date, weekday)]))
        updated = updated.replace(ARTICLES_MARKER, na + f"\n  {ARTICLES_MARKER}")
    else:
        # 后续运行：新 day-section 插入到末尾
        tn_close = html.find('</div>\n  <!-- end tab-news -->')
        if tn_close >= 0:
            updated = html[:tn_close] + f"\n{nd}\n" + html[tn_close:]
        else:
            pos = html.find('<div class="footer">')
            if pos < 0: print("❌ 找不到 footer 标记"); return False
            updated = html[:pos] + f"\n{nd}\n" + html[pos:]
        am = updated.find(ARTICLES_MARKER)
        if am >= 0: updated = updated[:am] + f"\n{na}\n" + updated[am:]
        # 将所有 day-section 按日期降序重排（最新在前）
        days = sorted(set(extract_days(updated)), reverse=True)
        if len(days) > 1:
            rebuilt = ''
            tab_start = updated.find('<div id="tab-news"')
            tag_end = updated.find('>', tab_start) + 1
            tab_end = updated.find('</div>\n  <!-- end tab-news -->')
            for d in days:
                m = re.search(rf'<section class="day-section" id="day-{re.escape(d)}">.*?</section>', updated, flags=re.DOTALL)
                if m:
                    rebuilt += '\n' + m.group()
            if tab_start >= 0 and tab_end > tag_end:
                updated = updated[:tag_end] + rebuilt + '\n' + updated[tab_end:]
        # 更新导航
        wd = [(d, WEEKDAY_NAMES[datetime.strptime(d,"%Y-%m-%d").weekday()]) for d in days]
        updated = re.sub(r'<nav class="day-nav">.*?</nav>', f'<nav class="day-nav">\n{build_nav(wd)}\n</nav>', updated, flags=re.DOTALL)
    updated, _ = prune_old(updated)
    if is_first:
        updated, _ = prune_old(updated)
    if gh_data and gh_data.get("items"):
        updated = inject_github(updated, gh_data)
    # 累积多日 GitHub 数据到 JS（跨进程：从已有 HTML 中读取再合并）
    all_gh = {}
    m = re.search(r'var ghData\s*=\s*({.*?});', updated, re.DOTALL)
    if m:
        try: all_gh = json.loads(m.group(1))
        except: pass
    all_gh[news["date"]] = (gh_data.get("items", []) if gh_data else [])
    gh_js = '<script>\n// GH_DATA_START\nvar ghData = ' + json.dumps({
        d: [{
            "full_name": p.get("full_name",""),
            "name": p.get("name",""),
            "stars": p.get("stars",0),
            "forks": p.get("forks",0),
            "language": p.get("language",""),
            "description": p.get("description",""),
            "_summary_cn": p.get("_summary_cn",""),
        } for p in (g if g else [])]
        for d, g in sorted(all_gh.items(), reverse=True)
    }, ensure_ascii=False) + ';\n'
    gh_js += 'function switchGhData(date) {\n'
    gh_js += '  var items = ghData[date];\n'
    gh_js += '  if (!items || !items.length) return;\n'
    gh_js += '  var cardsDiv = document.getElementById("github-cards");\n'
    gh_js += '  if (!cardsDiv) return;\n'
    gh_js += '  var h = "";\n'
    gh_js += '  for (var i=0; i<items.length; i++) {\n'
    gh_js += '    var p = items[i];\n'
    gh_js += '    var desc = (p._summary_cn || p.summary || p.description || "").slice(0,120);\n'
    gh_js += '    h += "<div class=\\"gh-card\\" onclick=\\"showGhProject("+i+")\\"><div class=\\"gh-card-top\\"><div class=\\"gh-card-title\\">"+p.name+"<span class=\\"gh-owner\\">"+p.full_name+"</span></div><button class=\\"bookmark-btn\\" onclick=\\"event.stopPropagation(); toggleBookmark("+i+")\\" id=\\"bm-"+i+"\\" data-full=\'"+p.full_name+"\'>☆</button></div><div class=\\"gh-card-meta\\"><span class=\\"gh-stars\\">"+p.stars+"</span> <span class=\\"gh-lang\\">"+(p.language||"")+"</span> <span class=\\"gh-forks\\">"+p.forks+"</span></div><div class=\\"gh-card-desc\\">"+desc+"</div></div>";\n'
    gh_js += '  }\n'
    gh_js += '  cardsDiv.innerHTML = h;\n'
    gh_js += '  updateBookmarkUI();\n'
    gh_js += '}\n'
    gh_js += 'ghProjects = ghData[Object.keys(ghData)[0]] || [];\n'
    gh_js += '// GH_DATA_END\n</script>'
    # 移除旧的 ghData 块（包括前后的 <script> 标签）
    gs = updated.find('// GH_DATA_START')
    ge = updated.find('// GH_DATA_END')
    if gs >= 0 and ge > gs:
        # 扩至前一个 <script 和后一个 </script>
        s1 = updated.rfind('<script', 0, gs)
        s2 = updated.find('</script>', ge)
        if s1 >= 0: gs = s1
        if s2 >= 0: ge = s2 + len('</script>')
        updated = updated[:gs] + gh_js + updated[ge:]
    else:
        be = updated.find('</body>')
        if be >= 0:
            updated = updated[:be] + gh_js + '\n' + updated[be:]
    HTML_PATH.write_text(updated, "utf-8")
    print("✅ index.html 已更新")
    return True

def save_obsidian(news):
    date, weekday, items = news["date"], news.get("weekday",""), news.get("items",[])
    OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
    dd = f"{date[:4]}年{int(date[5:7])}月{int(date[8:])}日"
    md = OBSIDIAN_VAULT / f"{date}-AI日报.md"
    lines = [f"---",f"title: AI日报 · {dd}",f"date: {date}",f"tags: [ai, 日报, 资讯]",f"---","",
             f"# 🤖 AI日报 · {dd} {weekday}","",f"共 {len(items)} 条资讯",""]
    for i, it in enumerate(items):
        lines += ["---","",f"### {i+1}. {it.get('title','')}","",
                  f"📰 来源：{it.get('source','综合')}"]
        if it.get("url"): lines.append(f"🔗 {it['url']}")
        lines.append("")
        s = it.get("summary","").split("\n\n")[0]
        lines.append((s[:200]+"…") if len(s)>200 else s)
        lines.append("")
    lines += ["---",f"*来源：多源聚合 · 更新时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}*"]
    md.write_text("\n".join(lines), "utf-8")
    print(f"✅ Obsidian：{md}")


def save_obsidian_bookmarks():
    """将书签同步到 Obsidian 收藏笔记"""
    OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
    md_file = OBSIDIAN_VAULT / "⭐ 已收藏的 GitHub 项目.md"
    lines = ["---", "title: ⭐ 已收藏的 GitHub 项目", f"updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             "tags: [ai, github, bookmarks, 收藏]", "---", "",
             "# ⭐ 已收藏的 GitHub 项目", "",
             "> 自动同步 — 每日更新时刷新", ""]
    if BOOKMARKS_PATH.exists():
        try:
            bm = json.loads(BOOKMARKS_PATH.read_text("utf-8"))
            if isinstance(bm, dict) and "items" in bm:
                items = bm["items"]
            elif isinstance(bm, list):
                items = bm
            else:
                items = []
            if not items:
                lines.append("暂无收藏的项目")
            else:
                for b in items:
                    fn = b.get("full_name", "")
                    name = b.get("name", fn.split("/")[-1] if "/" in fn else fn)
                    stars = b.get("stars", 0)
                    lang = b.get("language", "")
                    url = b.get("url", f"https://github.com/{fn}")
                    summary = b.get("summary", "")
                    bt = b.get("bookmarked_at", "")[:10]
                    lines += ["", f"### [{name}]({url})",
                              f"- ⭐ {stars} Stars &nbsp;|&nbsp; 🔤 {lang} &nbsp;|&nbsp; 📅 {bt}",
                              f"- {summary}" if summary else "",
                              f"- `{fn}`", ""]
        except:
            lines.append("数据加载失败")
    else:
        lines.append("暂无收藏数据")
    md_file.write_text("\n".join(lines), "utf-8")
    print(f"✅ Obsidian 书签：{md_file}")


def upload():
    try:
        r = subprocess.run(["scp",str(HTML_PATH),f"{SERVER}:{REMOTE_PATH}"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0: print("✅ 已上传服务器"); return True
        print(f"❌ 上传失败: {r.stderr}")
    except Exception as e: print(f"❌ 上传异常: {e}")
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sync-bookmarks":
        save_obsidian_bookmarks()
        sys.exit(0)
    news = load_news()
    if not news: print("❌ 未提供新闻数据"); sys.exit(1)
    gh = load_github(news["date"])
    info = f"📰 更新 {news['date']} AI 日报（{len(news.get('items',[]))} 条）"
    if gh and gh.get("items"): info += f" + 🔥 GitHub 项目 {len(gh['items'])} 个"
    print(info)
    ok = update_html(news, gh)
    if ok: upload()
    save_obsidian(news)
    print(f"\n{'='*40}\n  HTML: {'✅' if ok else '⏭️'}{' 上传: ✅' if ok and upload else ''}{'  GitHub: '+str(len(gh['items']))+' 个项目' if gh and gh.get('items') else ''}\n  🌐 http://82.156.80.178/ai-daily/")
