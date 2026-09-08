import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_json_ld

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    contamination_risk_pages = []
    
    for url, html in html_cache.items():
        json_ld = extract_json_ld(html)
        product_count = 0
        for block in json_ld:
            if block.get('@type') == 'Product':
                product_count += 1
                
        # If a single page has many un-nested products, it risks contamination
        if product_count > 3:
            contamination_risk_pages.append(url)
            
    if contamination_risk_pages:
        findings.append(Finding(
            id="INTEGRITY-001",
            title="High Semantic Confusion Risk (Attribute Contamination)",
            category="semantic_integrity",
            type="risk",
            severity="medium",
            confidence=0.8,
            affected_pages=contamination_risk_pages[:5],
            evidence=[EvidenceItem(source_type="json_ld", url=u, detail="Multiple top-level Product entities found, risking cross-product attribute contamination.") for u in contamination_risk_pages[:5]],
            mechanism="When multiple products are adjacent without strict scoping (e.g. ItemList), language models can mix their attributes.",
            ai_impact="An AI might state that Product A has Product B's price or features.",
            root_cause="Category or Related Products sections are injecting full top-level Product schemas.",
            suggested_action=ActionRecommendation(
                summary="Properly nest related products or use ItemList schema.",
                priority="P2",
                implementation="Use ItemList for category pages. For related products on a product page, use the `isRelatedTo` or `isSimilarTo` properties.",
                verification="Check that only one main Product entity exists at the root of the JSON-LD.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
