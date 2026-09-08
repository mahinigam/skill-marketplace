import sys
import os
import json
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType
from shared.utilities.extractors import extract_json_ld, extract_visible_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    missing_freshness = []
    corroboration_failures = []
    
    # Internal Corroboration Matrix: We track facts stated across multiple pages.
    # If Page A says "Price: $50" and Page B says "Price: $60" for the same product, it fails corroboration.
    fact_matrix = {}
    
    for url, html in html_cache.items():
        json_blocks = extract_json_ld(html)
        has_freshness = False
        
        for block in json_blocks:
            # Check for freshness
            if 'dateModified' in block or 'datePublished' in block:
                has_freshness = True
                
            # Populate fact matrix (e.g. price per SKU)
            if 'sku' in block and 'offers' in block:
                sku = str(block['sku'])
                offers = block['offers']
                if isinstance(offers, dict) and 'price' in offers:
                    price = str(offers['price'])
                    if sku not in fact_matrix:
                        fact_matrix[sku] = []
                    fact_matrix[sku].append((url, price))
                    
        # Check visible text for dates if JSON-LD missing
        if not has_freshness:
            text = extract_visible_text(html)
            if re.search(r'\b(20\d{2}[-/]\d{2}[-/]\d{2})\b', text):
                has_freshness = True
                
        if not has_freshness:
            missing_freshness.append(url)
            
    # Analyze Fact Matrix for Corroboration Failures
    for sku, claims in fact_matrix.items():
        unique_prices = set([c[1] for c in claims])
        if len(unique_prices) > 1:
            # Conflicting facts found internally!
            corroboration_failures.append((sku, claims))

    if missing_freshness:
        findings.append(Finding(
            id="FRESH-001",
            title="Missing Freshness Signals",
            category="Discoverability",
            type=FindingType.DEFECT,
            severity="low",
            confidence=0.9,
            affected_pages=missing_freshness[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="Lacks dateModified or datePublished in structured data, and no visible dates found.") for u in missing_freshness[:5]],
            mechanism="AI models prioritize 'fresh' data for volatile facts (pricing, events). Without explicit dates, older indexed data may be considered stale and dropped.",
            ai_impact="Model may refuse to answer queries requiring current information.",
            suggested_action=ActionRecommendation(
                summary="Add dateModified to structured data.",
                priority="P3",
                implementation="Include dateModified in WebPage or Article schema so AIs know the content is up to date.",
                verification="Validate JSON-LD contains dateModified.",
                effort="low",
                expected_impact="low"
            )
        ))
        
    if corroboration_failures:
        evidence = []
        affected = []
        for sku, claims in corroboration_failures[:3]:
            detail = f"SKU {sku} has conflicting prices: " + ", ".join([f"{c[1]} on {c[0]}" for c in claims])
            affected.extend([c[0] for c in claims])
            evidence.append(EvidenceItem(source_type="json-ld", url=claims[0][0], detail=detail))
            
        findings.append(Finding(
            id="CORR-001",
            title="Internal Fact Corroboration Failure",
            category="Semantics",
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.98,
            affected_pages=list(set(affected))[:5],
            evidence=evidence,
            mechanism="AI systems cross-reference facts (RAG). If the site internally contradicts itself (e.g. product page vs category page pricing), confidence plummets.",
            ai_impact="Citation dropped due to internal contradiction / hallucination risk.",
            suggested_action=ActionRecommendation(
                summary="Ensure data consistency across all views.",
                priority="P1",
                implementation="Use a single source of truth for pricing/attributes across category lists and product detail pages.",
                verification="Audit JSON-LD across lists vs details for the same SKU.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
