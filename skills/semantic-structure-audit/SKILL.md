---
name: semantic-structure-audit
description: Audits JSON-LD structured data and schema.org usage to ensure important entities and facts are machine-readable and consistent with visible text.
allowed-tools: []
---

# Semantic Structure Audit

## When to use
Use this skill to determine if a website is missing structured data (JSON-LD), or if the existing structured data is invalid, incomplete, or conflicts with visible content.

## Inputs
- `AuditContext` containing sampled pages and their extracted JSON-LD.

## Procedure
1. Extract JSON-LD blocks from the page structure.
2. Validate the presence of critical schema types (e.g. Product, Organization, Article, FAQPage).
3. Cross-reference the extracted structured data fields (name, description, price) against the explicit visible DOM facts to detect conflicts.
4. Generate findings if structured data is entirely missing, invalid, incomplete, or conflicts with the visible content.

## Output
Appends Findings to the `AuditContext`.
