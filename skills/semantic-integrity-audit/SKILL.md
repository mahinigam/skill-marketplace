---
name: semantic-integrity-audit
description: Audits semantic integrity and attribute ownership to detect category confusion and cross-product attribute contamination.
allowed-tools: []
---

# Semantic Integrity Audit

## When to use
Use this skill to detect if multiple products or entities are presented in a way that causes their attributes (like price, features) to mix up, known as semantic contamination.

## Inputs
- `AuditContext` containing sampled pages and structured data.

## Procedure
1. Detect all prices on the page using regex patterns on visible text.
2. Perform upward DOM traversal (`BeautifulSoup` parents) to determine the owning semantic container for each price.
3. Classify prices as `primary` (`<main>`, `<article>`), `auxiliary` (`<aside>`, `<nav>`, `<footer>`), or `orphaned` (no semantic boundaries, just `<div>` soup).
4. Evaluate boundary conditions: Flag orphaned prices on product pages, and detect "bleed" where auxiliary prices differ from primary prices (while safely ignoring legitimate cart/subtotal/tax markers).
5. Check if multiple distinct products or entities appear in the structured data without clear parent-child relationships.
6. Generate findings if high semantic confusion or DOM boundary failures are detected.

## Output
Appends Findings to the `AuditContext`.
