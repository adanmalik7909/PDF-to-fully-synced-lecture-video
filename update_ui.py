import os

file_path = r'c:\Users\PMLS\Desktop\Prototype\SmartStudyInstructor\frontend\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Emojis in Left Panel
content = content.replace('📚 Manage Courses', 'Manage Courses')
content = content.replace('🧑‍🎓 Track Students', 'Track Students')
content = content.replace('🤖 AI-Powered Insights', 'AI-Powered Insights')

# Emojis in Headings & Text
content = content.replace('Welcome back 👋', 'Welcome back')
content = content.replace('Join as Teacher 🎓', 'Join as Teacher')
content = content.replace('Check your inbox 📬', 'Check your inbox')
content = content.replace('You\'re all set! 🎉', 'You\'re all set!')
content = content.replace('Send Verification Code 📧', 'Send Verification Code')
content = content.replace('Verify & Create Account ✓', 'Verify & Create Account')

# Update input wrapper icons
email_svg = '<svg class="icon svg-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>'
pass_svg = '<svg class="icon svg-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>'
user_svg = '<svg class="icon svg-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'

content = content.replace('<span class="icon">✉️</span>', email_svg)
content = content.replace('<span class="icon">🔒</span>', pass_svg)
content = content.replace('<span class="icon">👤</span>', user_svg)

# Replace Eye Icon with sleek text
content = content.replace('<span class="eye-icon" onclick="togglePassword(\'loginPassword\', this)">👁</span>', '<span class="eye-icon" onclick="togglePassword(\'loginPassword\', this)" style="font-size:0.85rem; font-weight:600; color:var(--gray);">Show</span>')
content = content.replace('<span class="eye-icon" onclick="togglePassword(\'signupPassword\', this)">👁</span>', '<span class="eye-icon" onclick="togglePassword(\'signupPassword\', this)" style="font-size:0.85rem; font-weight:600; color:var(--gray);">Show</span>')

# Update JS for togglePassword
content = content.replace('el.innerText = \'🙈\';', 'el.innerText = \'Hide\';')
content = content.replace('el.innerText = \'👁\';', 'el.innerText = \'Show\';')

# Update strength label texts
content = content.replace('<span style="color:#EF4444">🔴 Weak password</span>', '<span style="color:#EF4444">Weak password</span>')
content = content.replace('<span style="color:#F97316">🟠 Fair password</span>', '<span style="color:#F97316">Fair password</span>')
content = content.replace('<span style="color:#EAB308">🟡 Good password</span>', '<span style=\"color:#EAB308\">Good password</span>')
content = content.replace('<span style="color:#22c55e">🟢 Strong password</span>', '<span style="color:#22c55e">Strong password</span>')

# Update checklist HTML
content = content.replace('<li id="reqLength" class="unmet">❌ At least 8 characters</li>', '<li id="reqLength" class="unmet"><span class="dot"></span> At least 8 characters</li>')
content = content.replace('<li id="reqUpper" class="unmet">❌ One uppercase letter (A–Z)</li>', '<li id="reqUpper" class="unmet"><span class="dot"></span> One uppercase letter (A–Z)</li>')
content = content.replace('<li id="reqNum" class="unmet">❌ One number (0–9)</li>', '<li id="reqNum" class="unmet"><span class="dot"></span> One number (0–9)</li>')
content = content.replace('<li id="reqSpec" class="unmet">❌ One special character (!@#$%^&*)</li>', '<li id="reqSpec" class="unmet"><span class="dot"></span> One special character (!@#$%^&*)</li>')

# Update match JS
content = content.replace('msg.innerHTML = \'✅ Passwords match\';', 'msg.innerHTML = \'Passwords match\';')
content = content.replace('msg.innerHTML = \'❌ Passwords do not match\';', 'msg.innerHTML = \'Passwords do not match\';')

# Add checklist dot CSS & fix svg
css_old = '''.checklist li.unmet {
            color: #EF4444;
        }'''
css_new = '''.checklist li.unmet {
            color: #EF4444;
        }

        .checklist li { display: flex; align-items: center; gap: 8px; }
        .checklist li .dot {
            width: 6px; height: 6px; border-radius: 50%; background: var(--gray); transition: background 0.3s;
        }
        .checklist li.met .dot { background: #22c55e; }
        .checklist li.unmet .dot { background: #EF4444; }

        .svg-icon {
            position: absolute; left: 16px; top: 50%; transform: translateY(-50%); color: var(--gray);
        }'''
content = content.replace(css_old, css_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("UI Updated.")
