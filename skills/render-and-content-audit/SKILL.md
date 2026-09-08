---
name: render-and-content-audit
description: Compares initial HTML with JS-rendered expectations to identify content only available after client-side hydration, which may be missed by AI assistants.
---

# Render and Content Audit

## When to use
Use this skill to detect if critical facts, entity information, or core content relies heavily on JS to be visible to search engines and AI assistants.

## Inputs
- `AuditContext` containing sampled pages.

## Procedure
1. Extract visible text from the initial HTML.
2. Estimate if the initial HTML lacks meaningful content (e.g. text-to-code ratio is extremely low, presence of `<div id="root"></div>` with no other content).
3. Generate findings if JS-dependent rendering hides facts.

## Output
Appends Findings to the `AuditContext`.
