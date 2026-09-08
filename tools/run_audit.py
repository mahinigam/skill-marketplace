import sys
import os
import argparse
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from skills.audit_orchestrator.scripts.orchestrate import run_orchestrator, generate_markdown_report

def main():
    parser = argparse.ArgumentParser(description="Run the AI Readiness Audit")
    parser.add_argument("url", help="The target URL to audit (e.g. https://example.com)")
    parser.add_argument("--output", help="Output JSON file path", default="audit.json")
    parser.add_argument("--report", help="Output Markdown report path", default="audit.md")
    
    args = parser.parse_args()
    
    if not args.url.startswith("http"):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)
        
    print(f"Running audit on {args.url}")
    
    try:
        report = run_orchestrator(args.url)
        
        with open(args.output, "w") as f:
            # We use model_dump_json because we are using pydantic models
            f.write(report.model_dump_json(indent=2))
        print(f"Saved machine-readable JSON to {args.output}")
        
        md_content = generate_markdown_report(report)
        with open(args.report, "w") as f:
            f.write(md_content)
        print(f"Saved human-readable Markdown to {args.report}")
        
    except Exception as e:
        print(f"Audit failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
