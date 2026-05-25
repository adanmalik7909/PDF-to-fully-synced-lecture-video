with open("c:\\Users\\PMLS\\Desktop\\Prototype\\SmartStudyInstructor\\backend\\rendering\\templates\\_base.css.j2", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "heading" in line or "zoom-active" in line:
        clean_line = line.strip().encode('ascii', errors='ignore').decode('ascii')
        print(f"Line {idx+1}: {clean_line}")
