import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_visible_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    boundary_failures = []
    
    for url, html in html_cache.items():
        text = extract_visible_text(html)
        
        # Look for multiple distinct prices in the text as a proxy for bad semantic boundaries
        prices = re.findall(r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*', text)
        if len(set(prices)) > 3:
            # Check if this is a listing page or details page. 
            # If it's a details page with > 3 prices, it's likely bleeding related products or cart totals.
            if 'product' in url.lower() or 'detail' in url.lower():
                # Differentiate legitimate global prices (cart totals) from boundary bleed
                # Legitimate cart prices usually appear near "cart", "total", "subtotal"
                # If we have 4+ prices and they aren't labeled "cart", it's semantic bleed.
                cart_matches = len(re.findall(r'(cart|total|subtotal)', text, re.IGNORECASE))
                
                if cart_matches < 2:
                    boundary_failures.append((url, list(set(prices))))
                
    if boundary_failures:
        evidence = [EvidenceItem(
            source_type="html", 
            url=u[0], 
            detail=f"Found {len(u[1])} distinct prices on a single product page: {', '.join(u[1][:3])}... (Likely sidebar/related products bleeding into main content)"
        ) for u in boundary_failures[:5]]
        
        findings.append(Finding(
            id="SEM-001",
            title="Semantic Boundary Failure: Content Bleed",
            category=FindingCategory.SEMANTICS,
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.85,
            affected_pages=[u[0] for u in boundary_failures],
            evidence=evidence,
            mechanism="Without clear semantic tags (e.g. <main>, <aside>), AI scrapers ingest headers, sidebars (related products), and footers as primary content.",
            ai_impact="AI quotes the price of a 'related product' or 'cart total' instead of the actual product requested.",
            suggested_action=ActionRecommendation(
                summary="Enclose core content in <main> and auxiliary content in <aside>.",
                priority="P1",
                implementation="Wrap related products, sidebars, and nav elements in <aside> or <nav> to exclude them from the primary node.",
                verification="Parse page with a basic article extractor (like Readability) and ensure only the main product remains.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
