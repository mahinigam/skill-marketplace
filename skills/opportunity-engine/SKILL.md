---
name: opportunity-engine
description: Generates proactive recommendations to improve AI discoverability and engagement, even when explicit defects are absent.
---

# Opportunity Engine

## When to use
Use this skill to move beyond defect detection. It looks for architectural optimizations like FAQ expansion, better entity linking, or machine-readable fact tables that would proactively strengthen the brand's presence in AI models.

## Inputs
- `AuditContext` containing the full set of findings and page data.

## Procedure
1. Check if the site lacks an explicit FAQ schema.
2. Check if the site lacks comparison content for products.
3. Check if there are weak entity relationships.
4. Generate proactive Opportunity records.

## Output
Appends Opportunities to the `AuditContext`.
