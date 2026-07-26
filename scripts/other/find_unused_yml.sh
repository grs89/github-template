#!/bin/bash
for file in $(find . -type f \( -name "*.yml" -o -name "*.yaml" \) -not -path "*/.git/*" -not -path "*/.venv/*" | sed 's|^\./||'); do
  base=$(basename "$file")
  count=$(rg -F "$base" -g '!find_unused_yml.sh' | grep -v "^$file:" | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "$file"
  fi
done
