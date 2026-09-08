---
name: entity-resolution-audit
description: Analyzes brand, organization, and product names across the website to detect entity ambiguity or inconsistent identity signals.
---

# Entity Resolution Audit

## When to use
Use this skill when you want to ensure the website presents a clear, unambiguous entity identity to AI systems. Ambiguous identities cause AI assistants to confuse the brand with competitors or general terms.

## Inputs
- `AuditContext` containing sampled pages and structured data.

## Procedure
1. Extract organization names, brand names, and aliases from visible text and JSON-LD.
2. Check if multiple distinct identities are used interchangeably without strong canonical linking.
3. Generate findings if identity signals are weak or highly ambiguous.

## Output
Appends Findings to the `AuditContext`.
