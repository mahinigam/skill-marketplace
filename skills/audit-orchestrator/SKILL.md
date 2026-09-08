---
name: audit-orchestrator
description: The main entrypoint for the AI Readiness Intelligence Engine. Coordinates the execution of all other audit skills, merges findings, correlates root causes, scores severity, and generates the final reports.
---

# Audit Orchestrator

## When to use
Use this skill as the single entrypoint to run a comprehensive AI readiness audit on a target website.

## Inputs
- `target_url`: The website URL to audit.

## Procedure
1. Initialize the `AuditContext`.
2. Discover pages using `SiteCrawler`.
3. Fetch HTML for discovered pages.
4. Delegate to specialized audit skills sequentially.
5. Consolidate findings and calculate the AI Readiness Score and Severity levels.
6. Generate the final machine-readable JSON report and human-readable Markdown report.

## Output
Emits the final JSON report according to the required schema, and a Markdown report.
