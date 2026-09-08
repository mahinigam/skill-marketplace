import sys
import os
from urllib.parse import urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_title, extract_visible_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    generic_routing_pages = []
    poor_context_pages = []
    
    for url, html in html_cache.items():
        title = extract_title(html) or ""
        text = extract_visible_text(html)
        parsed = urlparse(url)
        
        # Check for generic routing: deep URL but title/content looks like homepage
        if len(parsed.path) > 1 and parsed.path != '/':
            if "home" in title.lower() and len(text) < 500:
                generic_routing_pages.append(url)
                
        # Check for poor context: Page lacks clear H1 or next steps (very crude heuristic)
        if len(text) < 100:
            poor_context_pages.append(url)
            
    if generic_routing_pages:
        findings.append(Finding(
            id="LANDING-001",
            title="Generic Routing / Context Discontinuity",
            category="engagement",
            type="defect",
            severity="high",
            confidence=0.85,
            affected_pages=generic_routing_pages[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="Deep link resolves to generic homepage-like content.") for u in generic_routing_pages[:5]],
            mechanism="When users click an AI citation expecting specific facts, landing on a generic page breaks context and increases bounce rate.",
            user_impact="High recovery cost to find the referenced information.",
            suggested_action=ActionRecommendation(
                summary="Ensure deep links resolve to specific, relevant content.",
                priority="P1",
                implementation="Fix redirects that push deep URLs to the homepage. Ensure canonical URLs point to the specific content.",
                verification="Visit the URL and verify it shows the expected specific content.",
                effort="low",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
