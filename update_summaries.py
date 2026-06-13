import json

BRIEFS = {
    "affaan-m/ECC": "ECC 是一个 AI 编码智能体性能优化系统，集成了技能（Skills）、本能（Instincts）、记忆（Memory）和安全（Security）等核心能力，支持 Claude Code、Codex、OpenCode、Cursor 等多种 AI 编码工具。",
    "nexu-io/open-design": "Open Design 是一个本地优先的开源设计工具，支持 259+ 技能、142+ 设计系统，能生成 HTML/PDF/PPTX/MP4 等多种格式输出，是 Claude Design 的开源替代方案。",
    "NousResearch/hermes-agent": "Hermes Agent 是一个功能完整的开源 AI Agent 框架，支持终端、QQ、Telegram、Discord 等多平台运行，内置记忆系统、技能系统、定时任务和网关服务。",
    "addyosmani/agent-skills": "Agent Skills 是一个生产级工程技能集合，为 AI 编码 Agent 提供标准化的工程实践能力，让 AI 能更好地处理代码审查、测试、部署等开发任务。",
    "Leonxlnx/taste-skill": "Taste Skill 是一个 AI 审美技能包，通过精心设计的系统提示词让 AI 生成的界面拥有更好的布局、排版、动效和间距，告别千篇一律的模板风格。",
    "HKUDS/nanobot": "Nanobot 是一个轻量级开源 AI Agent，专为工具调用、聊天和个人助手场景设计，可本地部署，支持多种 LLM 后端。",
    "colbymchenry/codegraph": "CodeGraph 是一个预索引的代码知识图谱，自动同步代码变更，为 Claude Code、Codex、Gemini 等 Agent 提供更少 Token 消耗的代码上下文理解能力。",
    "farion1231/cc-switch": "cc-switch 是一个跨平台桌面 All-in-One 助手，支持一键切换 Claude Code、Codex、OpenCode、OpenClaw、Gemini CLI 和 Hermes Agent 等多种 AI 编码工具。",
    "x1xhlol/system-prompts-and-models-of-ai-tools": "收集了 Claude Code、Cursor、Devin、Windsurf、v0 等数十种 AI 编码工具的系统提示词（System Prompt）和内部模型信息，是最大的 AI 工具提示词公开集合。",
    "mvanhorn/last30days-skill": "Last30Days 是一个 AI Agent 技能，能跨 Reddit、X（Twitter）、YouTube 等平台搜索任意话题过去30天的内容，并按点赞、喜欢和互动评分排序。",
}

with open("C:/Users/7777/OpenCode/7s_project/ai-daily/github_projects.json", encoding="utf-8") as f:
    data = json.load(f)

for p in data["items"]:
    fn = p["full_name"]
    if fn in BRIEFS:
        p["summary"] = BRIEFS[fn]
        print(f"✅ {fn}: {len(BRIEFS[fn])} chars")
    else:
        desc = p.get("description", "")
        p["summary"] = desc if len(desc) > 30 else f"{p['name']} 是一个 AI 智能体相关项目。"
        print(f"⚠️ {fn}: 使用 description 后备")

with open("C:/Users/7777/OpenCode/7s_project/ai-daily/github_projects.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 已更新所有项目的中文摘要")
