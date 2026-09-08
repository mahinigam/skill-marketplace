import sys
import os
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType
from shared.utilities.extractors import extract_title, extract_visible_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    poor_citation_pages = []
    
    for url, html in html_cache.items():
        soup = BeautifulSoup(html, 'html.parser')
        title = extract_title(html)
        text = extract_visible_text(html)
        
        # Check Citation Destination Quality
        # 1. Is there an immediate H1 that confirms the intent?
        h1 = soup.find('h1')
        has_h1 = h1 is not None and len(h1.get_text(strip=True)) > 2
        
        # 2. Are there aggressive popups/walls in the raw DOM? (e.g. fixed overlays)
        has_wall = False
        overlays = soup.find_all(lambda tag: tag.name == 'div' and tag.get('class') and any('modal' in c.lower() or 'popup' in c.lower() or 'overlay' in c.lower() for c in tag.get('class')))
        if overlays:
            has_wall = True
            
        # 3. Context continuity (Does the title match the H1?)
        title_h1_mismatch = False
        if title and h1:
            title_words = set(title.lower().split())
            h1_words = set(h1.get_text(strip=True).lower().split())
            # If there's barely any overlap, it's a continuity break
            if len(title_words.intersection(h1_words)) == 0:
                title_h1_mismatch = True
                
        if not has_h1 or has_wall or title_h1_mismatch:
            poor_citation_pages.append((url, not has_h1, has_wall, title_h1_mismatch))
            
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
            title="Poor Citation Destination Quality (Intent Continuity Break)",
            category="Engagement",
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

    context.findings.extend(findings)
    return context
