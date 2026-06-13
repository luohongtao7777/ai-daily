import json, base64, subprocess, time, sys
from pathlib import Path

# 读取本地数据
with open("/mnt/c/Users/7777/OpenCode/7s_project/ai-daily/github_projects.json", encoding="utf-8") as f:
    data = json.load(f)

names = [p["full_name"] for p in data["items"]]
print(f"🔍 拉取 {len(names)} 个 README…")

for p in data["items"]:
    fn = p["full_name"]
    print(f"  {fn}... ", end="", flush=True)
    try:
        r = subprocess.run(
            ["curl", "-s", f"https://api.github.com/repos/{fn}/readme"],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            d = json.loads(r.stdout)
            if "content" in d and d["content"]:
                decoded = base64.b64decode(d["content"]).decode("utf-8", errors="replace")
                p["_readme_raw"] = decoded[:3000]
                print(f"✅ {len(decoded[:3000])} chars")
            else:
                p["_readme_raw"] = ""
                print(f"⏭️ {d.get('message','')}")
        else:
            p["_readme_raw"] = ""
            print("❌ curl fail")
    except Exception as e:
        p["_readme_raw"] = ""
        print(f"❌ {e}")
    time.sleep(0.3)

# 写回
with open("/mnt/c/Users/7777/OpenCode/7s_project/ai-daily/github_projects.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成!")
for p in data["items"]:
    print(f"  {p['full_name']}: {len(p.get('_readme_raw',''))} chars")
