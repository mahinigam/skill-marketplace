---
name: entity-resolution-audit
description: Analyzes brand, organization, and product names across the website to detect entity ambiguity or inconsistent identity signals.
allowed-tools: []
license: MIT
---

# Entity Resolution Audit

## When to use
Use this skill when you want to ensure the website presents a clear, unambiguous entity identity to AI systems. Ambiguous identities cause AI assistants to confuse the brand with competitors or general terms.

## Inputs
- `AuditContext` containing sampled pages and structured data.

## Procedure
1. Extract organization names, brand names, and aliases from visible text and JSON-LD structured data.
2. Apply fallback extraction (e.g., checking `<title>`, `<h1>`, and canonical tags) if primary signals are missing.
3. Check if multiple distinct identities or conflicting brand signals are used interchangeably without strong canonical linking.
4. Generate findings if entity identity signals are weak, highly ambiguous, or contradictory across the page.

## Output
Appends Findings to the `AuditContext`.
