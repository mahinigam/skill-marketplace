import sys
import os
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_json_ld, extract_title

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    brand_names = set()
    
    for url, html in html_cache.items():
        # Check titles
        title = extract_title(html)
        if title:
            # simple heuristic: split by | or - and take the last part
            parts = [p.strip() for p in title.replace('|', '-').split('-')]
            if len(parts) > 1:
                brand_names.add(parts[-1])
                
        # Check JSON-LD
        json_ld = extract_json_ld(html)
        for block in json_ld:
            if block.get('@type') in ('Organization', 'Brand'):
                name = block.get('name')
                if isinstance(name, str):
                    brand_names.add(name)
                    
    # If we found multiple contradictory brand names
    if len(brand_names) > 3:
        findings.append(Finding(
            id="ENT-001",
            title="Entity Ambiguity / Inconsistent Naming",
            category="entity_trust",
            type="risk",
            severity="medium",
            confidence=0.8,
            evidence=[EvidenceItem(source_type="mixed", url=context.target.url, detail=f"Found multiple candidate brand identities: {list(brand_names)}")],
            mechanism="When several different things share a name or the identity is weak, an AI system can mix them up.",
            ai_impact="AI assistants might associate facts with the wrong entity.",
            suggested_action=ActionRecommendation(
                summary="Standardize brand naming across title tags and structured data.",
                priority="P2",
                implementation="Ensure all pages use a single, canonical brand name in their <title> suffix and Organization JSON-LD.",
                verification="Check that extracted organization names resolve to exactly one canonical name.",
                effort="low",
                expected_impact="medium"
            )
        ))

    context.findings.extend(findings)
    return context
