---
name: freshness-and-corroboration-audit
description: Audits the freshness of information and internal consistency of facts (e.g. price, dates) across the website to prevent AI assistants from serving stale information.
---

# Freshness and Corroboration Audit

## When to use
Use this skill to detect if a website provides conflicting information internally, or if it lacks freshness signals (dateModified, ETag) which might cause an AI to doubt the accuracy of the facts.

## Inputs
- `AuditContext` containing sampled pages and structured data.

## Procedure
1. Extract dates from `datePublished`, `dateModified`, sitemap `lastmod`, or HTTP `Last-Modified`.
2. Extract common facts (e.g. price) across pages to detect contradictions.
3. Generate findings if important claims are contradictory or freshness signals are consistently missing.

## Output
Appends Findings to the `AuditContext`.
