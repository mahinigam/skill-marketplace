import json
import os
import sys
import re
import yaml

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # 1. Check marketplace.json
    manifest_path = os.path.join(root_dir, 'marketplace.json')
    if not os.path.exists(manifest_path):
        print("FAIL: marketplace.json not found.")
        sys.exit(1)
        
    with open(manifest_path, 'r') as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError:
            print("FAIL: marketplace.json is not valid JSON.")
            sys.exit(1)
            
    # 2. Check entrypoint
    skills = manifest.get('skills', [])
    entrypoints = [s for s in skills if s.get('entrypoint') is True]
    
    if len(entrypoints) != 1:
        print(f"FAIL: Expected exactly 1 entrypoint, found {len(entrypoints)}.")
        sys.exit(1)
        
    if entrypoints[0].get('id') != 'audit-orchestrator':
        print("WARNING: Entrypoint is not 'audit-orchestrator', this might be non-standard.")
        
    # 3. Check skill folders and SKILL.md
    for skill in skills:
        path = skill.get('path')
        skill_id = skill.get('id')
        if not path:
            print(f"FAIL: Skill {skill_id} missing 'path'.")
            sys.exit(1)
            
        skill_dir = os.path.join(root_dir, path)
        if not os.path.isdir(skill_dir):
            print(f"FAIL: Skill directory not found at {path}.")
            sys.exit(1)
            
        # Ensure path matches ID
        if not path.endswith(skill_id):
            print(f"FAIL: Skill path {path} does not match skill ID {skill_id}.")
            sys.exit(1)
            
        skill_md = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_md):
            print(f"FAIL: SKILL.md missing in {path}.")
            sys.exit(1)
            
        with open(skill_md, 'r') as f:
            content = f.read()
            if not content.startswith('---'):
                print(f"FAIL: SKILL.md in {path} does not start with YAML frontmatter '---'.")
                sys.exit(1)
                
            # Parse YAML frontmatter
            match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            if not match:
                print(f"FAIL: SKILL.md in {path} has malformed YAML frontmatter.")
                sys.exit(1)
                
            try:
                frontmatter = yaml.safe_load(match.group(1))
            except yaml.YAMLError:
                print(f"FAIL: SKILL.md in {path} has invalid YAML syntax in frontmatter.")
                sys.exit(1)
                
            if 'name' not in frontmatter or 'description' not in frontmatter:
                print(f"FAIL: SKILL.md in {path} frontmatter must contain 'name' and 'description'.")
                sys.exit(1)
                
    # 4. Check README
    if not os.path.isfile(os.path.join(root_dir, 'README.md')):
        print("FAIL: README.md not found at root.")
        sys.exit(1)

    print("SUCCESS: Marketplace validation passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
