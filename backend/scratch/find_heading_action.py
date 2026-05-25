with open("c:\\Users\\PMLS\\Desktop\\Prototype\\SmartStudyInstructor\\backend\\rendering\\templates\\_timeline_engine.js.j2", "r", encoding="utf-8") as f:
    lines = f.readlines()

output = []
for idx, line in enumerate(lines):
    if "heading_action" in line:
        clean_line = line.strip().encode('ascii', errors='ignore').decode('ascii')
        output.append(f"Line {idx+1}: {clean_line}")

with open("c:\\Users\\PMLS\\Desktop\\Prototype\\SmartStudyInstructor\\backend\\scratch\\heading_action_lines.txt", "w", encoding="utf-8") as f_out:
    f_out.write("\n".join(output))
