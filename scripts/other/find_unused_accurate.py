import os
import re

# 1. Get all YML files
yml_files = []
for root, dirs, files in os.walk('.'):
    if '.git' in root or '.venv' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.yml') or file.endswith('.yaml'):
            yml_files.append(os.path.join(root, file).replace('./', ''))

# 2. Read only valid source/doc files to search in
search_files = []
for root, dirs, files in os.walk('.'):
    if '.git' in root or '.venv' in root or 'node_modules' in root:
        continue
    for file in files:
        if file == 'CHANGELOG.md' or file.endswith('.json') or file.endswith('.py') or file.endswith('.sh') or file.endswith('.log'):
            continue
        if file.endswith('.yml') or file.endswith('.yaml') or file.endswith('.md'):
            try:
                with open(os.path.join(root, file), 'r') as f:
                    content = f.read()
                    search_files.append((os.path.join(root, file).replace('./', ''), content))
            except:
                pass

entrypoints = [
    ".gitlab-ci.yml"
]
for f in yml_files:
    if f.startswith('03-start/'):
        entrypoints.append(f)

unused = []
for yml in yml_files:
    if yml in entrypoints:
        continue
    
    basename = os.path.basename(yml)
    used = False
    
    for path, content in search_files:
        if path == yml:
            continue
            
        # Check if basename is mentioned in another YML or MD (excluding CHANGELOG)
        if basename in content:
            used = True
            break
            
    if not used:
        unused.append(yml)

for u in unused:
    print(u)
