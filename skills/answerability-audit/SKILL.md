---
name: answerability-audit
description: Evaluates if a machine could construct a correct answer to an important user question from the available page evidence without guessing.
allowed-tools: []
license: MIT
---

# Answerability Audit

## When to use
Use this skill to determine if the page actually answers the user's implicit questions when referred by an AI. A page might have content, but if it lacks specific answers to basic queries (like price, features), the AI won't cite it.

## Inputs
- `AuditContext` containing sampled pages and their text content.

## Procedure
1. Define 8 synthetic question intents: `purchase_decision`, `identity`, `specification`, `trust`, `location`, `freshness`, `use_case`, and `comparison`.
2. Map triggers (URL paths and visible text) to dynamically determine relevance per page.
3. Apply a weighted scoring algorithm: critical intents (e.g., purchase with `weight=3.0`) impact the score more heavily than secondary intents (`weight=1.0`), preventing sparse but correctly focused pages from being unfairly penalized.
4. Extract facts purely from visible text (to simulate AI extraction) and score facts as 1.0 (found unambiguously), 0.5 (ambiguous), or 0.0 (missing).
5. Generate findings if the final weighted answerability score falls to or below 0.5.

## Output
Appends Findings to the `AuditContext`.
