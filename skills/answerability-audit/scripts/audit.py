import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_visible_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    unanswerable_product_pages = []
    
    for url, html in html_cache.items():
        text = extract_visible_text(html).lower()
        
        # Heuristic: if it looks like a product page (e.g. contains 'buy', 'cart', 'product')
        # but has no numbers resembling a price, or lacks feature descriptions.
        if 'product' in url.lower() or 'buy' in text or 'add to cart' in text:
            # Check for price presence
            has_price = bool(re.search(r'\$\d+|\d+\s*(usd|eur|gbp)', text))
            if not has_price:
                unanswerable_product_pages.append(url)
                
    if unanswerable_product_pages:
        findings.append(Finding(
            id="ANS-001",
            title="Product Pages Lack Clear Pricing/Specification Answers",
            category="answerability",
            type="defect",
            severity="high",
            confidence=0.85,
            affected_pages=unanswerable_product_pages[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="Appears to be a product page but lacks explicit price formatting visible to text extraction.") for u in unanswerable_product_pages[:5]],
            mechanism="If an AI is asked 'How much is X?', it cannot confidently answer if the price is an image or hidden in un-parseable formats.",
            ai_impact="AI will state it doesn't know the price or will drop the citation.",
            suggested_action=ActionRecommendation(
                summary="Ensure product specifications and prices are in plain text.",
                priority="P1",
                implementation="Add explicit text blocks for price, specifications, and availability. Do not use images for text.",
                verification="Run a text extraction tool and verify the price is clearly readable.",
                effort="low",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
