import sys
import os
import re
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_json_ld

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    missing_dates_pages = []
    extracted_prices = {} # product_url: list of prices found
    
    for url, html in html_cache.items():
        # Check structured data for dates
        json_ld = extract_json_ld(html)
        has_date = False
        for block in json_ld:
            if block.get('datePublished') or block.get('dateModified'):
                has_date = True
            
            # Extract prices for contradiction check
            if block.get('@type') in ['Product', 'Offer']:
                price = None
                if 'offers' in block:
                    offers = block['offers']
                    if isinstance(offers, dict):
                        price = offers.get('price')
                    elif isinstance(offers, list) and len(offers) > 0:
                        price = offers[0].get('price')
                elif 'price' in block:
                    price = block.get('price')
                    
                if price:
                    extracted_prices.setdefault(url, []).append(str(price))
                    
        if not has_date:
            missing_dates_pages.append(url)
            
    # Contradiction check on prices within the same page (e.g. schema says one thing)
    contradicting_pages = []
    for url, prices in extracted_prices.items():
        if len(set(prices)) > 1:
            contradicting_pages.append(url)
            
    if contradicting_pages:
        findings.append(Finding(
            id="FRESH-001",
            title="Conflicting Facts (Price) on Page",
            category="freshness",
            type="defect",
            severity="critical",
            confidence=1.0,
            affected_pages=contradicting_pages[:5],
            evidence=[EvidenceItem(source_type="json_ld", url=u, detail=f"Found conflicting prices: {extracted_prices[u]}") for u in contradicting_pages[:5]],
            mechanism="When facts conflict on the same page, AI assistants lose confidence and may hallucinate or refuse to answer.",
            suggested_action=ActionRecommendation(
                summary="Ensure all structured data blocks report the same price.",
                priority="P0",
                implementation="Review the templates generating JSON-LD and ensure they draw from a single source of truth for pricing.",
                verification="Check that extracted price facts are identical.",
                effort="low",
                expected_impact="high"
            )
        ))
        
    if len(missing_dates_pages) > len(html_cache) / 2 and len(html_cache) > 0:
        findings.append(Finding(
            id="FRESH-002",
            title="Missing Freshness Signals",
            category="freshness",
            type="observation",
            severity="low",
            confidence=0.9,
            evidence=[EvidenceItem(source_type="html", url=context.target.url, detail="Majority of pages lack dateModified or datePublished signals.")],
            suggested_action=ActionRecommendation(
                summary="Add dateModified to structured data.",
                priority="P3",
                implementation="Include dateModified in WebPage or Article schema so AIs know the content is up to date.",
                verification="Validate JSON-LD contains dateModified.",
                effort="medium",
                expected_impact="low"
            )
        ))

    context.findings.extend(findings)
    return context
