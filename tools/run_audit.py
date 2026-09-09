import argparse
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import importlib

orchestrate = importlib.import_module("skills.audit-orchestrator.scripts.orchestrate")
run_orchestrator = orchestrate.run_orchestrator
generate_markdown_report = orchestrate.generate_markdown_report

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
        
        report_dict = report.model_dump()
        
        # Format evidence as a plain string to strictly comply with the rubric's string schema,
        # while preserving the rich structured objects in a new 'evidence_details' field.
        for item_list in [report_dict.get("findings", []), report_dict.get("opportunities", [])]:
            for item in item_list:
                structured_evidence = item.get("evidence", [])
                item["evidence_details"] = structured_evidence
                item["evidence"] = "\n".join([f"- {ev['detail']} (Source: {ev['url']})" for ev in structured_evidence])

        with open(args.output, "w") as f:
            f.write(json.dumps(report_dict, indent=2))
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
