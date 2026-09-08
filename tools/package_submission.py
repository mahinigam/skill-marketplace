import os
import sys
import zipfile
import shutil
import subprocess

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    print("Running validation...")
    val_script = os.path.join(root_dir, 'tools', 'validate_marketplace.py')
    result = subprocess.run([sys.executable, val_script])
    if result.returncode != 0:
        print("Validation failed. Cannot package.")
        sys.exit(1)
        
    dist_dir = os.path.join(root_dir, 'dist')
    os.makedirs(dist_dir, exist_ok=True)
    zip_path = os.path.join(dist_dir, 'ai-readiness-intelligence-marketplace.zip')
    
    # Files/folders to exclude
    excludes = ['__pycache__', '.git', '.env', 'dist', 'venv', '.pytest_cache', 'audit.json', 'audit.md']
    
    print(f"Creating zip archive at {zip_path}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Mutate dirs in place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in excludes and not d.startswith('.')]
            
            for file in files:
                if file in excludes or file.endswith('.pyc') or file.startswith('.'):
                    continue
                
                file_path = os.path.join(root, file)
                # Ensure we don't zip the zip file itself
                if file_path == zip_path:
                    continue
                    
                arcname = os.path.relpath(file_path, root_dir)
                # The prompt specifies the zip should open TO the marketplace root folder:
                # "ai-readiness-intelligence-marketplace/marketplace.json"
                arcname = os.path.join('ai-readiness-intelligence-marketplace', arcname)
                
                zipf.write(file_path, arcname)
                
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Archive created. Size: {size_mb:.2f} MB")
    
    if size_mb > 50:
        print("WARNING: Size exceeds 50 MB limit!")
    else:
        print("SUCCESS: Ready for submission.")

if __name__ == "__main__":
    main()
