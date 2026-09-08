import sys
import os
import re
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_title, extract_visible_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    poor_citation_pages = []
    claim_visibility_failures = []
    
    for url, html in html_cache.items():
        soup = BeautifulSoup(html, 'html.parser')
        title = extract_title(html)
        text = extract_visible_text(html)
        
        # 1. Structural Intent Continuity
        h1 = soup.find('h1')
        has_h1 = h1 is not None and len(h1.get_text(strip=True)) > 2
        
        has_wall = False
        overlays = soup.find_all(lambda tag: tag.name == 'div' and tag.get('class') and any('modal' in c.lower() or 'popup' in c.lower() or 'overlay' in c.lower() for c in tag.get('class')))
        if overlays:
            has_wall = True
            
        title_h1_mismatch = False
        if title and h1:
            title_words = set(title.lower().split())
            h1_words = set(h1.get_text(strip=True).lower().split())
            if len(title_words.intersection(h1_words)) == 0:
                title_h1_mismatch = True
                
        if not has_h1 or has_wall or title_h1_mismatch:
            poor_citation_pages.append((url, not has_h1, has_wall, title_h1_mismatch))
            
        # 2. Claim-based Context Continuity
        # Simulate AI citing a price. We expect the price to be visible immediately (first ~1000 chars of visible text).
        prices = re.findall(r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*', text)
        if prices:
            primary_price = prices[0]
            # Check where it appears in the raw visible text
            idx = text.find(primary_price)
            # If it's buried deep in the text (e.g. footer or requires scrolling), it fails continuity
            if idx > 1500:
                claim_visibility_failures.append((url, primary_price, idx))
            
    if poor_citation_pages:
        evidence = []
        for url, no_h1, wall, mismatch in poor_citation_pages[:5]:
            issues = []
            if no_h1: issues.append("Missing/Empty H1")
            if wall: issues.append("Aggressive Overlay/Modal found in DOM")
            if mismatch: issues.append("Title and H1 completely mismatch")
            evidence.append(EvidenceItem(source_type="html", url=url, detail=", ".join(issues)))
            
        findings.append(Finding(
            id="LAND-001",
            title="Poor Citation Destination Quality (Structural Break)",
            category=FindingCategory.ENGAGEMENT,
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.9,
            affected_pages=[u[0] for u in poor_citation_pages],
            evidence=evidence,
            mechanism="When a user clicks an AI citation link, they expect immediate corroboration of the AI's answer. Missing H1s, mismatched titles, or immediate popups break intent continuity, causing high bounce rates.",
            user_impact="User abandons the site immediately because the destination doesn't clearly match the AI's promise.",
            suggested_action=ActionRecommendation(
                summary="Ensure clear intent continuity upon landing.",
                priority="P1",
                implementation="Align the <title> and <h1>. Ensure the primary answer/fact is visible immediately without dismissing modals.",
                verification="Check that the H1 clearly reflects the page topic and no blocking modals render on initial load.",
                effort="low",
                expected_impact="high"
            )
        ))

    if claim_visibility_failures:
        evidence = [EvidenceItem(
            source_type="html", 
            url=u[0], 
            detail=f"Claimed fact '{u[1]}' is buried at character index {u[2]} of visible text, likely below the fold."
        ) for u in claim_visibility_failures[:5]]
        
        findings.append(Finding(
            id="LAND-002",
            title="Poor Citation Destination Quality (Claim Buried)",
            category=FindingCategory.ENGAGEMENT,
            type=FindingType.DEFECT,
            severity="medium",
            confidence=0.85,
            affected_pages=[u[0] for u in claim_visibility_failures],
            evidence=evidence,
            mechanism="Users clicking an AI citation want to instantly verify the specific claim (e.g., price). If it's below the fold, they bounce.",
            user_impact="High bounce rate as users fail to instantly verify the AI's claim.",
            suggested_action=ActionRecommendation(
                summary="Move core facts above the fold.",
                priority="P2",
                implementation="Ensure primary facts (price, stock, core specs) are visible immediately upon load without scrolling.",
                verification="Visually inspect the page to ensure the fact is above the fold.",
                effort="medium",
                expected_impact="medium"
            )
        ))

    context.findings.extend(findings)
    return context
