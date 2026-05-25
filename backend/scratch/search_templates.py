import os

def search_text(root, text):
    for root_dir, dirs, files in os.walk(root):
        for f in files:
            if f.endswith('.py') or f.endswith('.html') or f.endswith('.j2') or f.endswith('.css') or f.endswith('.js'):
                path = os.path.join(root_dir, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        if text in content:
                            print(f"Found in {path}")
                            lines = content.splitlines()
                            for idx, line in enumerate(lines):
                                if text in line:
                                    print(f"  Line {idx+1}: {line.strip()[:120]}")
                except Exception as e:
                    pass

search_text("c:\\Users\\PMLS\\Desktop\\Prototype\\SmartStudyInstructor\\backend", "heading")
