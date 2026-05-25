import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

query = "visual_events"
target_dir = r"c:\Users\PMLS\Desktop\Prototype\SmartStudyInstructor\backend"

with open(r"C:\Users\PMLS\.gemini\antigravity\brain\e93356b2-f9c8-418f-8fa0-a7945cc9c06b\scratch\search_results.txt", "w", encoding="utf-8") as out:
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith((".py", ".j2", ".js", ".html")):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if query.lower() in content.lower():
                        lines = content.splitlines()
                        out.write(f"=== {file} ===\n")
                        for idx, line in enumerate(lines):
                            if query.lower() in line.lower():
                                out.write(f"{idx+1}: {line}\n")
                except Exception as e:
                    out.write(f"Error reading {file}: {e}\n")
print("Done searching.")
