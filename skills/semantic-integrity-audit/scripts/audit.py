import sys
import os
from bs4 import BeautifulSoup
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    cross_contamination_pages = []
    
    for url, html in html_cache.items():
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for multiple products/entities on a single page
        products = soup.find_all(lambda tag: tag.name in ['div', 'li', 'article'] and 
                                             tag.get('class') and 
                                             any('product' in c.lower() or 'item' in c.lower() for c in tag.get('class')))
        
        if len(products) > 1:
            # Check if attributes (like prices) are properly scoped inside the product boundaries.
            # If we find global prices outside the product scopes, or ambiguous hierarchical headers, we flag it.
            global_text = soup.get_text()
            prices = re.findall(r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*', global_text)
            
            scoped_prices = 0
            for p in products:
                scoped_prices += len(re.findall(r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*', p.get_text()))
                
            # If there are more prices on the page than inside product boundaries, it's a boundary bleed
            if len(prices) > scoped_prices + 1: # allow 1 global cart price
                cross_contamination_pages.append(url)
                
    if cross_contamination_pages:
        findings.append(Finding(
            id="INT-001",
            title="Attribute Boundary Bleed (Cross-Contamination)",
            category="Semantics",
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.85,
            affected_pages=cross_contamination_pages[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="Found attributes (prices) outside strict product DOM boundaries.") for u in cross_contamination_pages[:5]],
            mechanism="When extracting from list pages, AI relies on DOM boundaries. Attributes floating outside clear parent-child structures often get attributed to the wrong entity.",
            ai_impact="Model mis-attributes price/feature to the wrong product, leading to hallucinations.",
            suggested_action=ActionRecommendation(
                summary="Ensure strict DOM containment for entity attributes.",
                priority="P1",
                implementation="Wrap every product and its attributes (price, title, image) in a single semantic container (e.g., `<article>`). Avoid global floating prices.",
                verification="Inspect DOM tree to ensure no orphaned attributes exist outside entity containers.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
