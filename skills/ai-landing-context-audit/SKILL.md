---
name: ai-landing-context-audit
description: Assesses on-site engagement quality when a user lands on the page from an AI citation, ensuring context continuity and intent match.
allowed-tools: []
---

# AI Landing Context Audit

## When to use
Use this skill to determine if the destination URLs cited by an AI assistant preserve the user's context and help them continue their journey without high recovery cost.

## Inputs
- `AuditContext` containing sampled pages and their HTML content.

## Procedure
1. Check if the page `<title>` and main heading (`<h1>`) clearly identify the subject the user is landing to see.
2. Simulate an AI answering a specific claim and verify that the exact claim text passes the early-page visibility proxy (using a character-index threshold in the visible text) rather than being buried.
3. Detect generic routing (e.g., redirecting all deep links to the homepage) or disruptive full-page modals.
4. Check for clear navigation or next-step actions.
5. Generate findings if the landing context is poor or breaks continuity.

## Output
Appends Findings to the `AuditContext`.
