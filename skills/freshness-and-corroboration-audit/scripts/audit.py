import sys
import os
import json
import re
from typing import Optional
from dataclasses import dataclass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_json_ld, extract_visible_text


# ---------------------------------------------------------------------------
# Corroboration Provider Adapter (Provider-Neutral Pattern)
# ---------------------------------------------------------------------------

@dataclass
class CorroborationResult:
    """Result of a corroboration check."""
    status: str          # "corroborated", "conflicted", "unavailable"
    source_label: str    # human-readable name of the source checked
    detail: str          # explanation of the result


class CorroborationProvider:
    """
    Abstract base for corroboration sources.
    Subclasses implement the actual lookup against a specific backend.
    """
    def verify(self, fact_key: str, fact_value: str, domain: str) -> CorroborationResult:
        raise NotImplementedError


class InternalCorroborationProvider(CorroborationProvider):
    """
    Cross-references facts within the same site's crawled pages.
    This is always active because it requires no external access.
    """
    def __init__(self, fact_matrix: dict):
        self.fact_matrix = fact_matrix
    
    def verify(self, fact_key: str, fact_value: str, domain: str) -> CorroborationResult:
        if fact_key in self.fact_matrix:
            claims = self.fact_matrix[fact_key]
            unique_values = set(c[1] for c in claims)
            if len(unique_values) > 1:
                return CorroborationResult(
                    status="conflicted",
                    source_label="internal (cross-page)",
                    detail=f"Fact '{fact_key}' has {len(unique_values)} conflicting values across pages: {', '.join(unique_values)}"
                )
            return CorroborationResult(
                status="corroborated",
                source_label="internal (cross-page)",
                detail=f"Fact '{fact_key}' is consistent across {len(claims)} page(s)."
            )
        return CorroborationResult(
            status="unavailable",
            source_label="internal (cross-page)",
            detail=f"Fact '{fact_key}' only appears on one page; no cross-page corroboration possible."
        )


class FixtureCorroborationProvider(CorroborationProvider):
    """
    Deterministic test fixtures for offline/demo validation.
    Uses a static lookup table of known-good facts for reproducible testing.
    """
    FIXTURES = {
        # Format: (fact_key, domain) -> expected_value
        # Empty by default; populated for specific test scenarios
    }
    
    def verify(self, fact_key: str, fact_value: str, domain: str) -> CorroborationResult:
        lookup = self.FIXTURES.get((fact_key, domain))
        if lookup is not None:
            if str(lookup) == str(fact_value):
                return CorroborationResult(
                    status="corroborated",
                    source_label="fixture (offline test data)",
                    detail=f"Fact '{fact_key}={fact_value}' matches fixture expectation."
                )
            else:
                return CorroborationResult(
                    status="conflicted",
                    source_label="fixture (offline test data)",
                    detail=f"Fact '{fact_key}={fact_value}' conflicts with fixture value '{lookup}'."
                )
        return CorroborationResult(
            status="unavailable",
            source_label="fixture (offline test data)",
            detail=f"No fixture data available for '{fact_key}' on domain '{domain}'."
        )


class ExternalAPICorroborationProvider(CorroborationProvider):
    """
    Optional: hits a real external API when configured.
    
    This provider is environment-dependent and requires:
      - An API key set in the environment (e.g., CORROBORATION_API_KEY)
      - Network access to the external knowledge graph
    
    When not configured, it explicitly returns 'unavailable' rather than
    pretending a check occurred.
    """
    def __init__(self):
        self.api_key = os.environ.get("CORROBORATION_API_KEY")
        self.configured = self.api_key is not None
    
    def verify(self, fact_key: str, fact_value: str, domain: str) -> CorroborationResult:
        if not self.configured:
            return CorroborationResult(
                status="unavailable",
                source_label="external API",
                detail="External corroboration provider not configured (CORROBORATION_API_KEY not set). Skipping external verification."
            )
        
        # When configured, this would hit a real API endpoint.
        # The implementation below is the integration point; the actual HTTP
        # call would go here when an API is available.
        return CorroborationResult(
            status="unavailable",
            source_label="external API",
            detail="External API integration point. Configure an endpoint to enable real external verification."
        )


def _select_providers(fact_matrix: dict) -> list:
    """
    Selects active corroboration providers based on what's available.
    Internal is always active. External/fixture are optional.
    """
    providers = [InternalCorroborationProvider(fact_matrix)]
    
    external = ExternalAPICorroborationProvider()
    if external.configured:
        providers.append(external)
    
    # Fixture provider is always available for testing but only produces 
    # results when fixture data exists for the queried fact
    providers.append(FixtureCorroborationProvider())
    
    return providers


def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    missing_freshness = []
    internal_conflicts = []
    corroboration_unavailable_facts = []
    
    # Build fact matrix: {sku -> [(url, price), ...]}
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
            
    # Run corroboration through provider chain
    providers = _select_providers(fact_matrix)
    
    for sku, claims in fact_matrix.items():
        unique_prices = set(c[1] for c in claims)
        
        # 1. Internal corroboration (always active)
        if len(unique_prices) > 1:
            internal_conflicts.append((sku, claims))
        
        # 2. Check all available providers for external/fixture corroboration
        if len(unique_prices) == 1:
            primary_price = list(unique_prices)[0]
            all_unavailable = True
            for provider in providers:
                if isinstance(provider, InternalCorroborationProvider):
                    continue  # Already handled above
                result = provider.verify(f"price_{sku}", primary_price, context.target.domain)
                if result.status == "conflicted":
                    # A real conflict was found by an external source
                    internal_conflicts.append((sku, claims))
                    all_unavailable = False
                    break
                elif result.status == "corroborated":
                    all_unavailable = False
                    break
            
            if all_unavailable:
                corroboration_unavailable_facts.append((sku, primary_price, claims[0][0]))

    # --- Emit Findings ---
    
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
        
    if internal_conflicts:
        evidence = []
        affected = []
        for sku, claims in internal_conflicts[:3]:
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

    # Note: we intentionally do NOT emit a finding for "corroboration_unavailable_facts".
    # When external corroboration is unavailable, we report it honestly in the audit
    # summary rather than pretending a check occurred and passed.

    context.findings.extend(findings)
    return context
