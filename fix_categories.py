import os
import glob
import re

files = glob.glob('skills/*/scripts/audit.py')

for file in files:
    with open(file, 'r') as f:
        content = f.read()
    
    # Replace category="something" or category='something'
    content = re.sub(r'category=["\']discoverability["\']', 'category=FindingCategory.DISCOVERABILITY', content, flags=re.IGNORECASE)
    content = re.sub(r'category=["\']semantics["\']', 'category=FindingCategory.SEMANTICS', content, flags=re.IGNORECASE)
    content = re.sub(r'category=["\']engagement["\']', 'category=FindingCategory.ENGAGEMENT', content, flags=re.IGNORECASE)
    content = re.sub(r'category=["\']answerability["\']', 'category=FindingCategory.ENGAGEMENT', content, flags=re.IGNORECASE)
    content = re.sub(r'category=["\']machine_readability["\']', 'category=FindingCategory.DISCOVERABILITY', content, flags=re.IGNORECASE)
    
    # Also need to import FindingCategory
    if 'FindingCategory' not in content:
        content = content.replace('FindingType', 'FindingType, FindingCategory')
        
    with open(file, 'w') as f:
        f.write(content)
        
print("Fixed categories.")
