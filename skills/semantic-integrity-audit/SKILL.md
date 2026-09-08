---
name: semantic-integrity-audit
description: Audits semantic integrity and attribute ownership to detect category confusion and cross-product attribute contamination.
---

# Semantic Integrity Audit

## When to use
Use this skill to detect if multiple products or entities are presented in a way that causes their attributes (like price, features) to mix up, known as semantic contamination.

## Inputs
- `AuditContext` containing sampled pages and structured data.

## Procedure
1. Check if multiple distinct products or entities appear in the structured data of a single page without clear parent-child relationships.
2. Check for missing clear boundaries.
3. Generate findings if high semantic confusion risk is detected.

## Output
Appends Findings to the `AuditContext`.
