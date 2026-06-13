#!/usr/bin/env python3
"""合并涨星最快 + 总星数最高的项目"""
import json, subprocess, time

FILE = "C:/Users/7777/OpenCode/7s_project/ai-daily/github_projects.json"

# 读取已有数据
with open(FILE, encoding='utf-8') as f:
    data = json.load(f)

existing = {p['full_name']: p for p in data['items']}
print(f'现有涨星数据: {len(existing)} 个')

# 补充搜索：按总星数获取（补遗漏的知名项目）
MORE_QUERIES = [
    'claude-code+agent+stars:>10000',
    'ai-agent+framework+stars:>10000',
    'mcp-server+stars:>5000',
    'coding-agent+cli+stars:>5000',
]

all_items = list(existing.values())
seen = set(existing.keys())

for q in MORE_QUERIES:
    url = f'https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=10'
    r = subprocess.run(['curl', '-s', url], capture_output=True, text=True, timeout=15)
    if r.returncode == 0:
        try:
            results = json.loads(r.stdout).get('items', [])
            for item in results:
                fn = item['full_name']
                if fn in seen:
                    continue
                seen.add(fn)
                all_items.append({
                    'full_name': fn, 'name': item['name'], 'url': item['html_url'],
                    'description': item.get('description','') or '',
                    'stars': item['stargazers_count'], 'forks': item['forks_count'],
                    'language': item.get('language') or 'N/A',
                    'topics': item.get('topics',[]),
                    'open_issues': item['open_issues_count'],
                    'license': (item.get('license') or {}).get('spdx_id','') or 'N/A',
                    'created_at': (item.get('created_at') or '')[:10],
                    'updated_at': (item.get('updated_at') or '')[:10],
                    'category': '其他',
                })
        except:
            pass
    before = len(all_items)
    print(f'  {q}: +{before} 个')

# 排除不相关的项目
EXCLUDE_FNS = [
    'voltagent', 'ultraworker', 'garrytan/', 'juliusbrussee', 'safishamsi',
    'santifer/', 'egonex-ai', 'multica-ai', 'esengine/', 
]
all_items = [p for p in all_items 
             if not any(x in p['full_name'].lower() for x in EXCLUDE_FNS)]

# 合并后去重并评分（涨星 + 总星数）
from datetime import datetime
for p in all_items:
    created = p.get('created_at', '')
    days = 1
    if created:
        try:
            days = max((datetime.now() - datetime.strptime(created, '%Y-%m-%d')).days, 1)
        except:
            pass
    p['_growth_rate'] = round(p['stars'] / days, 1)

# 评分 = 总星数排名 × 0.4 + 涨星速度排名 × 0.6
sorted_by_stars = sorted(all_items, key=lambda p: -p['stars'])
sorted_by_growth = sorted(all_items, key=lambda p: -p['_growth_rate'])

rank_stars = {p['full_name']: i for i, p in enumerate(sorted_by_stars)}
rank_growth = {p['full_name']: i for i, p in enumerate(sorted_by_growth)}

n = len(all_items)
for p in all_items:
    rs = rank_stars.get(p['full_name'], n)
    rg = rank_growth.get(p['full_name'], n)
    p['_score'] = round(rs * 0.4 + rg * 0.6, 1)

# 按综合评分排序
all_items.sort(key=lambda p: p['_score'])
all_items = all_items[:12]  # 保留12个

# 去掉内部字段
clean = []
for p in all_items:
    clean.append({k: v for k, v in p.items() if not k.startswith('_')})

print(f'\n🏆 最终榜单 (涨星+热门 综合):')
for i, p in enumerate(clean, 1):
    print(f'  {i:2d}. ⭐{p["stars"]:>6d}  {p["full_name"]:45s}  [{p["language"]}]')

# 保存
out = {'updated_at': '2026-06-13 22:15', 'total': len(clean), 'items': clean}
with open(FILE.replace('/c/', 'C:/'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f'\n✅ 保存 {len(clean)} 个项目')
