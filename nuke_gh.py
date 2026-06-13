#!/usr/bin/env python3
"""彻底清理页面中所有 GitHub 相关内容，然后重建"""
import re, json
from pathlib import Path

BASE = Path(__file__).parent
INDEX_PATH = BASE / "index.html"

html = INDEX_PATH.read_text("utf-8")

def remove_matching_blocks(text, pattern):
    """移除所有匹配 pattern 的块，通过追踪div嵌套正确关闭"""
    result = []
    i = 0
    while i < len(text):
        m = re.search(pattern, text[i:])
        if not m:
            result.append(text[i:])
            break
        # 添加匹配之前的内容
        result.append(text[i:i + m.start()])
        # 跳过整个块（追踪div嵌套）
        pos = i + m.end()
        depth = 1
        while pos < len(text) and depth > 0:
            nxt_op = text.find('<div', pos)
            nxt_cl = text.find('</div>', pos)
            if nxt_cl == -1:
                break
            if nxt_op != -1 and nxt_op < nxt_cl:
                depth += 1
                pos = nxt_op + 1
            else:
                depth -= 1
                pos = nxt_cl + 1
        i = pos
    return ''.join(result)

# 1. 移除所有 id="tab-github" 的 div
html = remove_matching_blocks(html, r'<div[^>]*id="tab-github"[^>]*>')

# 2. 移除所有 class="github-section" 的 div
html = remove_matching_blocks(html, r'<div[^>]*class="github-section"[^>]*>')

# 3. 移除所有 class="github-header" 的 div
html = remove_matching_blocks(html, r'<div[^>]*class="github-header"[^>]*>')

# 4. 移除所有 class="tab-bar" 的 div
html = remove_matching_blocks(html, r'<div[^>]*class="tab-bar"[^>]*>')

# 5. 移除 id="tab-news" 的包裹（只移除标签本身）
html = re.sub(r'\s*<div id="tab-news" class="tab-pane active">', '\n', html, count=1)

# 6. 移除所有 gh-detail 块
html = remove_matching_blocks(html, r'<div id="gh-detail-\d+" class="article-item">')

# 7. 移除 loading div
html = remove_matching_blocks(html, r'<div[^>]*id="gh-loading"[^>]*>')

# 8. 移除 duplicate toasts
html = re.sub(r'\s*<div class="toast" id="toast">[\s\S]*?</div>', '', html)

# 9. 移除旧 JS 注入（从任何标记到脚本结尾）
for marker in ['// ===== Tab', 'var ghProjects =', '// ===== 收藏', '// ===== GitHub']:
    idx = html.find(marker)
    if idx >= 0:
        script_end = html.rfind('</script>', 0, html.find('</body>'))
        if script_end > idx:
            html = html[:idx] + html[script_end:]

# 10. 清理多余空行
html = re.sub(r'\n{4,}', '\n\n', html)

# 验证
v = lambda name: print(f'  {name}: {html.count(name)}')
print("=== 清理后 ===")
print(f'大小: {len(html):,}')
v('tab-bar')
v('tab-news')
v('tab-github')
v('github-section')
v('github-header')
v('gh-card')
v('gh-detail-')
v('ghProjects')
v('showGhProject')
v('bookmark-btn')

# 检查基础结构完整性
body_count = html.count('<body>')
body_end = html.count('</body>')
script_count = html.count('<script>')
script_end = html.count('</script>')
print(f'\n结构: body={body_count}/{body_end} script={script_count}/{script_end}')
assert body_count == 1 and body_end == 1, "body 标签不完整"
assert script_count == 1 and script_end == 1, "script 标签不完整"

INDEX_PATH.write_text(html, "utf-8")
print("\n✅ 清理完成，可以运行 rebuild_page.py")
print(f"   命令: python rebuild_page.py && scp index.html ubuntu@82.156.80.178:/var/www/html/ai-daily/")
