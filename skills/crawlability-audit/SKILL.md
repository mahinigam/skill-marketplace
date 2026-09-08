---
name: crawlability-audit
description: Audits a website for crawlability issues including robots.txt directives, sitemap presence, HTTP errors, canonical URLs, and page discoverability.
---

# Crawlability Audit

## When to use
Use this skill when diagnosing if a website is discoverable by search crawlers and AI assistants. If a page cannot be crawled, it effectively doesn't exist for AI systems.

## Inputs
- `AuditContext` containing the target URL and initial discovered pages.

## Procedure
1. Check if `robots.txt` exists and if it blocks important paths.
2. Check if a sitemap exists and is valid.
3. Assess the discoverability of sampled URLs.
4. Check for consistent canonicalization and HTTP errors (4xx, 5xx) on sampled pages.
5. Generate findings based on evidence of poor discoverability or crawlability blocks.

## Output
Appends Findings and Opportunities to the `AuditContext`.
