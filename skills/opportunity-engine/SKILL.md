---
name: opportunity-engine
description: Generates proactive recommendations to improve AI discoverability and engagement, even when explicit defects are absent.
allowed-tools: []
license: MIT
---

# Opportunity Engine

## When to use
Use this skill to move beyond defect detection. It looks for architectural optimizations like FAQ expansion, better entity linking, or machine-readable fact tables that would proactively strengthen the brand's presence in AI models.

## Inputs
- `AuditContext` containing the full set of findings and page data.

## Procedure
Execute a suite of proactive detectors across the site:
1. **OPP-001**: Check if the site lacks an explicit FAQ schema.
2. **OPP-002**: Check if product pages lack `AggregateRating` or `Review` schema data.
3. **OPP-003**: Check for a flat heading hierarchy (e.g., H1 without supporting H2/H3s).
4. **OPP-004**: Check for incomplete Product schema (missing description, image, or brand).
5. **OPP-005**: Check for missing `sameAs` links for entity authority.
6. **OPP-006**: Check for missing `SearchAction` within `WebSite` schema.
7. **OPP-007**: Check for missing `contactPoint` array within `Organization` schema.
8. Generate proactive Opportunity records for each detected architectural optimization.

## Output
Appends Opportunities to the `AuditContext`.
