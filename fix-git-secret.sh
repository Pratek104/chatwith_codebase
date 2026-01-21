#!/bin/bash

# This script removes the hardcoded API key from git history

echo "Removing hardcoded API key from git history..."

# Remove the file from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch app.py" \
  --prune-empty --tag-name-filter cat -- --all

# Add the fixed version
git add app.py

# Commit the fix
git commit -m "fix: remove hardcoded API key and use environment variables"

# Force push to remote
echo "Ready to force push. Run: git push origin main --force"
