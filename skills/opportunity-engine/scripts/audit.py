import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Opportunity, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_json_ld

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    opportunities = []
    
    has_faq = False
    
    for url, html in html_cache.items():
        json_ld = extract_json_ld(html)
        for block in json_ld:
            if block.get('@type') == 'FAQPage':
                has_faq = True
                break
                
    if not has_faq:
        opportunities.append(Opportunity(
            id="OPP-001",
            title="Implement FAQ Schema for High-Intent Questions",
            description="Proactively answering common AI queries (What is X? How much is X?) using FAQ schema increases the chance of direct citation.",
            evidence=[EvidenceItem(source_type="json_ld", url=context.target.url, detail="No FAQPage schema found across sampled pages.")],
            suggested_action=ActionRecommendation(
                summary="Create an FAQ page with FAQPage JSON-LD.",
                priority="P2",
                implementation="Identify top user queries and answer them directly in an FAQ section, marked up with schema.org/FAQPage.",
                verification="Check for FAQPage structured data on the FAQ page.",
                effort="medium",
                expected_impact="medium"
            )
        ))

    context.opportunities.extend(opportunities)
    return context
