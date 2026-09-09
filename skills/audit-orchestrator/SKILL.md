---
name: audit-orchestrator
description: The main entrypoint for the AI Readiness Intelligence Engine. Coordinates the execution of all other audit skills, merges findings, correlates root causes, scores severity, and generates the final reports.
allowed-tools: []
---

# Audit Orchestrator

## When to use
Use this skill as the single entrypoint to run a comprehensive AI readiness audit on a target website.

## Inputs
- `target_url`: The website URL to audit.

## Procedure
1. Initialize the `AuditContext` and `SiteCrawler`.
2. Discover pages using the `PageImportance` heuristic model (weighing depth, inbound links, sitemap presence, and commercial relevance).
3. Fetch HTML for discovered pages and store in cache.
4. Dynamically delegate to specialized audit skills sequentially based on `marketplace.json` manifest.
5. Fuse raw findings using multi-signal correlation (Jaccard similarity on mechanisms/pages + category/action matches) to group symptoms into root causes via connected-component clustering.
6. Calculate the AI Readiness Score across Discoverability, Semantics, and Engagement dimensions.
7. Generate the final machine-readable JSON report and human-readable Markdown report.

## Output
Emits the final JSON report according to the required schema, and a Markdown report.
