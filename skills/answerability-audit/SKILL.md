---
name: answerability-audit
description: Evaluates if a machine could construct a correct answer to an important user question from the available page evidence without guessing.
---

# Answerability Audit

## When to use
Use this skill to determine if the page actually answers the user's implicit questions when referred by an AI. A page might have content, but if it lacks specific answers to basic queries (like price, features), the AI won't cite it.

## Inputs
- `AuditContext` containing sampled pages and their text content.

## Procedure
1. Define synthetic question classes (identity, price, features, specifications).
2. For each page, analyze if it contains evidence that answers these questions (e.g., looks for pricing patterns if it's a product page).
3. Generate findings for gaps in answerability.

## Output
Appends Findings to the `AuditContext`.
