import sys
import os
import json
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_json_ld, extract_visible_text

class ExternalCorroborator:
    """
    Simulates external corroboration. In a real environment, this would hit 
    Bing/Google API, Wikidata, or a trusted 3rd party knowledge graph to 
    verify the claim.
    """
    @staticmethod
    def verify(fact_key: str, fact_value: str, domain: str) -> bool:
        # Mock logic: assume we queried an external graph and it mostly agrees,
        # but fails for very specific mock conditions to demonstrate the detector.
        if "contradict" in fact_value.lower():
            return False
        return True

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    missing_freshness = []
    internal_corroboration_failures = []
    external_corroboration_failures = []
    
    fact_matrix = {}
    
    for url, html in html_cache.items():
        json_blocks = extract_json_ld(html)
        has_freshness = False
        
        for block in json_blocks:
            if 'dateModified' in block or 'datePublished' in block:
                has_freshness = True
                
            if 'sku' in block and 'offers' in block:
                sku = str(block['sku'])
                offers = block['offers']
                if isinstance(offers, dict) and 'price' in offers:
                    price = str(offers['price'])
                    if sku not in fact_matrix:
                        fact_matrix[sku] = []
                    fact_matrix[sku].append((url, price))
                    
        if not has_freshness:
            text = extract_visible_text(html)
            if re.search(r'\b(20\d{2}[-/]\d{2}[-/]\d{2})\b', text):
                has_freshness = True
                
        if not has_freshness:
            missing_freshness.append(url)
            
    # Analyze Fact Matrix for Corroboration Failures
    for sku, claims in fact_matrix.items():
        unique_prices = set([c[1] for c in claims])
        
        # 1. Internal Corroboration
        if len(unique_prices) > 1:
            internal_corroboration_failures.append((sku, claims))
            
        # 2. External Corroboration (mock)
        else:
            primary_price = list(unique_prices)[0]
            if not ExternalCorroborator.verify(f"price_{sku}", primary_price, context.target.domain):
                external_corroboration_failures.append((sku, primary_price, claims[0][0]))

    if missing_freshness:
        findings.append(Finding(
            id="FRESH-001",
            title="Missing Freshness Signals",
            category=FindingCategory.DISCOVERABILITY,
            type=FindingType.DEFECT,
            severity="low",
            confidence=0.9,
            affected_pages=missing_freshness[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="Lacks dateModified or datePublished in structured data, and no visible dates found.") for u in missing_freshness[:5]],
            mechanism="AI models prioritize 'fresh' data for volatile facts. Without explicit dates, older indexed data may be considered stale and dropped.",
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
        
    if internal_corroboration_failures:
        evidence = []
        affected = []
        for sku, claims in internal_corroboration_failures[:3]:
            detail = f"SKU {sku} has conflicting prices: " + ", ".join([f"{c[1]} on {c[0]}" for c in claims])
            affected.extend([c[0] for c in claims])
            evidence.append(EvidenceItem(source_type="json-ld", url=claims[0][0], detail=detail))
            
        findings.append(Finding(
            id="CORR-001",
            title="Internal Fact Corroboration Failure",
            category=FindingCategory.SEMANTICS,
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.98,
            affected_pages=list(set(affected))[:5],
            evidence=evidence,
            mechanism="AI systems cross-reference facts (RAG). If the site internally contradicts itself, confidence plummets.",
            ai_impact="Citation dropped due to internal contradiction.",
            suggested_action=ActionRecommendation(
                summary="Ensure data consistency across all views.",
                priority="P1",
                implementation="Use a single source of truth for pricing/attributes.",
                verification="Audit JSON-LD across lists vs details for the same SKU.",
                effort="medium",
                expected_impact="high"
            )
        ))

    if external_corroboration_failures:
        evidence = []
        for sku, price, url in external_corroboration_failures[:3]:
            evidence.append(EvidenceItem(
                source_type="external_graph", 
                url=url, 
                detail=f"Price {price} for SKU {sku} conflicts with recognized 3rd-party knowledge graph data."
            ))
            
        findings.append(Finding(
            id="CORR-002",
            title="External Fact Corroboration Failure",
            category=FindingCategory.SEMANTICS,
            type=FindingType.DEFECT,
            severity="critical",
            confidence=0.85,
            affected_pages=[f[2] for f in external_corroboration_failures],
            evidence=evidence,
            mechanism="When a site's claims strongly deviate from the broad web consensus (external corroboration), LLMs penalize the source's trust score.",
            ai_impact="Model will refuse to use the site as a primary source for this fact.",
            suggested_action=ActionRecommendation(
                summary="Reconcile facts with external authoritative sources.",
                priority="P0",
                implementation="Ensure product specs and pricing match manufacturer or standardized global identifiers.",
                verification="Check if third-party APIs return the same facts.",
                effort="high",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
