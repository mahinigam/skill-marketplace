# Audit finding and evidence contract

This document summarizes the model-level contract for findings emitted by the audit skills. The Pydantic models in `shared/models/models.py` remain the implementation source of truth.

## Finding identity and classification

Each `Finding` has a stable `id`, human-readable `title`, and a `category` chosen from:

- `Discoverability`
- `Semantics`
- `Engagement`

Its `type` distinguishes a `defect`, `risk`, `opportunity`, or `observation`. Severity is currently represented as a string; use the established `critical`, `high`, `medium`, or `low` vocabulary. Confidence is numeric and should remain in the inclusive range from 0 to 1.

## Evidence requirements

Evidence should let a reviewer trace a conclusion back to an observed page or response. Each evidence item has:

- `source_type`: where the evidence came from, such as HTML, JSON-LD, robots.txt, sitemap, or an external corroboration source
- `url`: the observed source URL
- `detail`: a concise description of what was seen
- `observed_value` and `expected_value`: optional values that help explain a mismatch

Prefer concise, specific evidence over generic statements. Avoid storing credentials, personal data, or large raw page bodies in reports.

## Recommendation contract

Every finding carries a `suggested_action` with a summary, priority, implementation guidance, verification method, effort, and expected impact. Recommendations should describe a concrete next step and a way to confirm it worked. Keep priority values in the established `P0` through `P3` vocabulary.

## Regression-test checklist

When adding or changing an audit rule:

1. Add a positive fixture that triggers the finding for the intended reason.
2. Add a healthy fixture that should not trigger it, where practical.
3. Assert the finding ID and key evidence, not only a non-empty result.
4. Confirm confidence and scores stay in their documented ranges.
5. Run the validator and complete unit suite.

## Report schema note

The README documents the external report's schema and compatibility choices. If a report serialization field differs from the internal Pydantic model, update the report-generation code, tests, and documentation together rather than silently changing the interface.
