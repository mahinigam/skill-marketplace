---
name: render-and-content-audit
description: Compares initial HTML with JS-rendered expectations to identify content only available after client-side hydration, which may be missed by AI assistants.
allowed-tools: []
---

# Render and Content Audit

## When to use
Use this skill to detect if critical facts, entity information, or core content relies heavily on JS to be visible to search engines and AI assistants.

## Inputs
- `AuditContext` containing sampled pages.

## Procedure
1. Extract visible text from the raw HTTP (initial HTML) response to serve as the baseline.
2. Utilize Bounded Simulated Headless Rendering (e.g., via `Playwright` or simulated extraction) to extract post-hydration text.
3. Compare the baseline text to the post-hydration text.
4. Estimate if the initial HTML lacks meaningful content (e.g. text-to-code ratio is extremely low, presence of `<div id="root"></div>` with no other content).
5. Generate findings if critical facts or entity information rely entirely on JS-dependent rendering.

## Output
Appends Findings to the `AuditContext`.
