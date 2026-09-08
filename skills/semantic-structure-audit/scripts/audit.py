import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_json_ld, extract_visible_text

def extract_prices(text: str):
    # Extracts basic numeric prices
    matches = re.findall(r'[\$\€\£\₹\¥]\s*(\d+[\.,]?\d*)', text)
    return set([m.replace(',', '') for m in matches])

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    missing_json_ld_pages = []
    ambiguous_html_pages = []
    mismatched_facts_pages = []
    
    for url, html in html_cache.items():
        json_blocks = extract_json_ld(html)
        visible_text = extract_visible_text(html)
        visible_prices = extract_prices(visible_text)
        
        if not json_blocks:
            # Differentiate good HTML vs ambiguous HTML
            # Very basic proxy: does it have structural semantic tags?
            if '<article' in html or '<main' in html or '<section' in html:
                # Good HTML
                missing_json_ld_pages.append(url)
            else:
                ambiguous_html_pages.append(url)
        else:
            # Validate JSON-LD vs Visible Text (Fact Cross-Validation)
            for block in json_blocks:
                if 'offers' in block:
                    offers = block['offers']
                    if isinstance(offers, dict) and 'price' in offers:
                        json_price = str(offers['price'])
                        # Check if this exact price string is in visible prices
                        if json_price not in visible_prices and visible_prices:
                            mismatched_facts_pages.append((url, json_price, list(visible_prices)[0]))
                            
    if missing_json_ld_pages:
        findings.append(Finding(
            id="SEM-001",
            title="Missing structured data (JSON-LD) with clean HTML fallback",
            category=FindingCategory.SEMANTICS,
            type=FindingType.OPPORTUNITY,
            severity="medium",
            confidence=0.9,
            affected_pages=missing_json_ld_pages[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="No JSON-LD found, but HTML has clear semantic boundaries (<main>, <article>).") for u in missing_json_ld_pages[:5]],
            mechanism="AI bots can parse the clean HTML, but JSON-LD would make extraction cheaper and highly deterministic.",
            suggested_action=ActionRecommendation(
                summary="Add JSON-LD structured data for explicit fact exposure.",
                priority="P2",
                implementation="Add Product, Organization, or Article schema.",
                verification="Check for `<script type=\"application/ld+json\">` block.",
                effort="low",
                expected_impact="medium"
            )
        ))
        
    if ambiguous_html_pages:
        findings.append(Finding(
            id="SEM-002",
            title="Missing structured data AND ambiguous DOM structure",
            category=FindingCategory.SEMANTICS,
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.95,
            affected_pages=ambiguous_html_pages[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="No JSON-LD found, and HTML lacks semantic boundaries (<main>, <article>). Div soup.") for u in ambiguous_html_pages[:5]],
            mechanism="Without explicit boundaries or JSON-LD, AI parsers struggle to differentiate core content from navigation/footer noise.",
            ai_impact="Attributes may be misinterpreted, merged with unrelated content, or skipped entirely.",
            suggested_action=ActionRecommendation(
                summary="Implement Semantic HTML5 and JSON-LD.",
                priority="P1",
                implementation="Wrap core content in <main>/<article> and inject JSON-LD state.",
                verification="Validate HTML5 semantic structure.",
                effort="high",
                expected_impact="high"
            )
        ))
        
    if mismatched_facts_pages:
        evidence = [EvidenceItem(
            source_type="json-ld", 
            url=u[0], 
            detail=f"JSON-LD price ({u[1]}) contradicts visible text price (~{u[2]})."
        ) for u in mismatched_facts_pages[:5]]
        
        findings.append(Finding(
            id="SEM-003",
            title="Contradictory Facts: Structured Data vs Visible Text",
            category=FindingCategory.SEMANTICS,
            type=FindingType.DEFECT,
            severity="critical",
            confidence=0.95,
            affected_pages=[u[0] for u in mismatched_facts_pages],
            evidence=evidence,
            mechanism="When structured data contradicts visible text, modern AI models detect hallucination/deception risk and heavily down-rank the source.",
            ai_impact="Complete loss of trust. The citation will be rejected.",
            suggested_action=ActionRecommendation(
                summary="Synchronize JSON-LD output with frontend rendering state.",
                priority="P0",
                implementation="Ensure the data object feeding the JSON-LD `<script>` is the exact same object feeding the UI component (e.g. React props).",
                verification="Assert JSON-LD price == Visible DOM price.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
