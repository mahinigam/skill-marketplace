import sys
import os
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_json_ld

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    missing_sd_pages = []
    poor_sd_pages = []
    
    for url, html in html_cache.items():
        json_ld = extract_json_ld(html)
        if not json_ld:
            missing_sd_pages.append(url)
        else:
            # Check if it has useful types
            has_useful = False
            for block in json_ld:
                btype = block.get('@type', '')
                if isinstance(btype, str) and btype in ['Product', 'Organization', 'Article', 'FAQPage', 'WebSite']:
                    has_useful = True
                elif isinstance(btype, list) and any(t in ['Product', 'Organization', 'Article', 'FAQPage', 'WebSite'] for t in btype):
                    has_useful = True
            
            if not has_useful:
                poor_sd_pages.append(url)
                
    if missing_sd_pages:
        findings.append(Finding(
            id="SEM-001",
            title="Missing structured data (JSON-LD)",
            category="semantic_structure",
            type="defect",
            severity="high",
            confidence=0.95,
            affected_pages=missing_sd_pages[:5],
            evidence=[EvidenceItem(source_type="json_ld", url=u, detail="No JSON-LD schema markup found on the page.") for u in missing_sd_pages[:5]],
            mechanism="AI bots rely on structured data to easily extract factual attributes without parsing complex DOM structures.",
            ai_impact="Attributes may be misinterpreted or skipped.",
            root_cause="Templates do not include JSON-LD blocks.",
            suggested_action=ActionRecommendation(
                summary="Add JSON-LD structured data.",
                priority="P1",
                implementation="Add Product, Organization, or Article schema corresponding to the page's intent.",
                verification="Check for `<script type=\"application/ld+json\">` block in the HTML source.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
