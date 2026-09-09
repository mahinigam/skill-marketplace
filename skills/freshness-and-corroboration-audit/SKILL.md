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
1. Extract dates from `datePublished`, `dateModified`, sitemap `lastmod`, or HTTP `Last-Modified` headers to assess freshness signals.
2. Extract common facts (e.g. price) across pages to detect internal contradictions.
3. Utilize a provider-neutral adapter pattern (`CorroborationProvider`) to support multiple corroboration strategies:
   - `InternalCorroborationProvider`: Always active, cross-references facts across crawled pages within the same site.
   - `FixtureCorroborationProvider`: Uses deterministic test data for offline validation.
   - `ExternalAPICorroborationProvider`: Safely attempts external API calls or explicitly reports "unavailable" when not configured.
4. Generate findings if important claims are contradictory or freshness signals are consistently missing.

## Output
Appends Findings to the `AuditContext`.
