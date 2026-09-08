---
name: semantic-structure-audit
description: Audits JSON-LD structured data and schema.org usage to ensure important entities and facts are machine-readable and consistent with visible text.
---

# Semantic Structure Audit

## When to use
Use this skill to determine if a website is missing structured data (JSON-LD), or if the existing structured data is invalid, incomplete, or conflicts with visible content.

## Inputs
- `AuditContext` containing sampled pages and their extracted JSON-LD.

## Procedure
1. Check each page for the presence of JSON-LD blocks.
2. Validate the presence of important schema types (e.g. Product, Organization, Article).
3. Generate findings if structured data is entirely missing, or lacks essential fields (name, description, price).

## Output
Appends Findings to the `AuditContext`.
