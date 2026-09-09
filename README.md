# AI Readiness Intelligence Engine Marketplace

This is an Agent Skill Marketplace designed for the Adobe University Hackathon 2026 Round 3. It audits websites to determine their AI discoverability and on-site engagement quality.

## Objective

The core philosophy of this marketplace is:
> "Don't merely tell a company that its website has SEO issues. Explain why an AI agent may fail to discover, read, interpret, trust, quote, or successfully hand a user off to that website — then recommend the smallest high-impact changes that resolve the underlying cause."

## Skill Architecture

The marketplace consists of 10 distinct skills coordinated by a single entrypoint:

1. **`audit-orchestrator`** (ENTRYPOINT): Orchestrates the entire audit, merges findings, deduplicates root causes via evidence-graph correlation, calculates non-linear readiness scores, and generates the final JSON and Markdown reports.
2. **`crawlability-audit`**: Checks robots.txt, sitemaps, HTTP errors, and basic page discoverability.
3. **`render-and-content-audit`**: Detects if critical facts rely heavily on client-side JS using Simulated Headless Rendering (Bounded execution) with optional Playwright fallback.
4. **`semantic-structure-audit`**: Audits JSON-LD structured data vs. explicit visible DOM facts.
5. **`entity-resolution-audit`**: Analyzes brand and product names to detect identity ambiguity (uses title/H1 fallbacks).
6. **`freshness-and-corroboration-audit`**: Checks for staleness and internally conflicting information, with optional provider adapter for external corroboration (deterministic fixtures included for offline testing).
7. **`answerability-audit`**: Evaluates expected fact-coverage (e.g., price, availability) against natural language questions, penalizing ambiguous extraction.
8. **`semantic-integrity-audit`**: Detects attribute contamination, distinguishing legitimate global objects (e.g. cart totals) from boundary bleed.
9. **`ai-landing-context-audit`**: Simulates an AI answering a specific claim and verifies that claim passes the early-page visibility proxy (character-index threshold).
10. **`opportunity-engine`**: Generates proactive recommendations beyond explicit defects (e.g., FAQ expansions) supported by verifiable evidence.

## Input and Output Format

- **Input**: The orchestrator accepts a target URL string.
- **Output**: The orchestrator emits a structured `FinalAuditReport` in JSON containing:
  - `site`: The audited domain.
  - `audited_at`: The timestamp in ISO 8601 UTC.
  - `summary`: Count of findings by severity.
  - `findings`: A list of findings with evidence, severity, and suggested actions.
  - `opportunities`: Proactive recommendations.
  - `root_causes`: Consolidated root causes driving the findings.

> **Note on Schema Compliance**: The rubric's sample schema shows `"evidence"` as a plain string. Our implementation emits `"evidence"` as a list of structured objects (e.g., `[{"source_type": "html", "url": "...", "detail": "..."}]`). This is a deliberate superset (a "ceiling, not a floor") to provide richer, traceable diagnostic context while fully satisfying the required diagnostic payload.

## Usage

### Validate Marketplace
```bash
python tools/validate_marketplace.py
```

### Run an Audit
```bash
python tools/run_audit.py https://example.com --output audit.json --report audit.md
```

### Package Submission
```bash
python tools/package_submission.py
```

## Safety & Constraints
- **Read-Only**: The crawler only performs GET requests and does not submit forms or authenticate.
- **Bounded Runtime**: Crawler respects limits on pages and timeout rules to stay well within the < 5 minute runtime limit.
- **Provider-Neutral**: Core analysis operates deterministically without relying on paid APIs.
- **Robots.txt Respect**: Honors robots.txt directives and crawl-delay where appropriate.
