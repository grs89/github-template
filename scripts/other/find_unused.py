import os
import re

yml_files = []
for root, dirs, files in os.walk('.'):
    if '.git' in root or '.venv' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.yml') or file.endswith('.yaml'):
            yml_files.append(os.path.join(root, file).replace('./', ''))

all_content = []
for root, dirs, files in os.walk('.'):
    if '.git' in root or '.venv' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.log') or file == 'find_unused.py' or file == 'find_unused_yml.sh':
            continue
        try:
            with open(os.path.join(root, file), 'r') as f:
                content = f.read()
                all_content.append((os.path.join(root, file).replace('./', ''), content))
        except:
            pass

entrypoints = [
    ".gitlab-ci.yml"
]

unused = []
for yml in yml_files:
    if yml in entrypoints:
        continue
    
    used = False
    for path, content in all_content:
        if path == yml:
            continue
        
        # Check if the relative path is mentioned anywhere
        if yml in content:
            used = True
            break
            
        # Check if the basename is mentioned in an include statement
        basename = os.path.basename(yml)
        if re.search(r'(:|file:|- local:)\s*[\'"]?.*' + re.escape(basename), content):
            used = True
            break
            
        # Check if it's mentioned in markdown documentation
        if path.endswith('.md') and basename in content:
            used = True
            break
            
    if not used:
        unused.append(yml)

for u in unused:
    print(f"UNUSED: {u}")
