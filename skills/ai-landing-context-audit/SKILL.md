---
name: ai-landing-context-audit
description: Assesses on-site engagement quality when a user lands on the page from an AI citation, ensuring context continuity and intent match.
---

# AI Landing Context Audit

## When to use
Use this skill to determine if the destination URLs cited by an AI assistant preserve the user's context and help them continue their journey without high recovery cost.

## Inputs
- `AuditContext` containing sampled pages and their HTML content.

## Procedure
1. Check if the page title clearly identifies the subject.
2. Check for clear navigation or next-step actions.
3. Detect generic routing (e.g., redirecting all deep links to the homepage).
4. Generate findings if the landing context is poor.

## Output
Appends Findings to the `AuditContext`.
