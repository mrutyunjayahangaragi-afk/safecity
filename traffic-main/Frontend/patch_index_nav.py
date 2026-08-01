import os

index_path = r'c:\safe\traffic-main\Frontend\index.html'
with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Try adding to nav-links
if 'dashboard.html' not in content:
    nav_link_html = '<a href="dashboard.html" class="nav-link" style="color:var(--accent);">🏙️ Smart City</a>'
    
    # Let's insert it before the first nav-link
    if '<a href="#features" class="nav-link">Features</a>' in content:
        content = content.replace('<a href="#features" class="nav-link">Features</a>', nav_link_html + '\n      <a href="#features" class="nav-link">Features</a>')
    elif '<div class="nav-links">' in content:
        content = content.replace('<div class="nav-links">', '<div class="nav-links">\n      ' + nav_link_html)
        
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added dashboard link to index.html")
