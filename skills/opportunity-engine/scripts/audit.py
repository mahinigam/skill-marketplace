import sys
import os
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Opportunity, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_json_ld, extract_visible_text


def _check_faq_opportunity(html_cache: dict, context: AuditContext) -> list:
    """Detect missing FAQ schema across all pages."""
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
            confidence=0.8,
            impact="medium",
            priority="P2",
            suggested_action=ActionRecommendation(
                summary="Create an FAQ page with FAQPage JSON-LD.",
                priority="P2",
                implementation="Identify top user queries and answer them directly in an FAQ section, marked up with schema.org/FAQPage.",
                verification="Check for FAQPage structured data on the FAQ page.",
                effort="medium",
                expected_impact="medium"
            )
        ))
    return opportunities


def _check_comparison_opportunity(html_cache: dict, context: AuditContext) -> list:
    """Detect missing comparison/review data on product pages."""
    opportunities = []
    product_pages_without_reviews = []
    
    for url, html in html_cache.items():
        if 'product' not in url.lower() and 'item' not in url.lower():
            continue
            
        json_ld = extract_json_ld(html)
        has_review_data = False
        for block in json_ld:
            if block.get('@type') == 'Product':
                if 'aggregateRating' in block or 'review' in block:
                    has_review_data = True
                    break
        
        text = extract_visible_text(html)
        if not has_review_data and ('review' not in text.lower() and 'rating' not in text.lower()):
            product_pages_without_reviews.append(url)
    
    if product_pages_without_reviews:
        opportunities.append(Opportunity(
            id="OPP-002",
            title="Add Structured Review/Rating Data for Comparison Queries",
            description="AI comparison queries ('Which is better, X or Y?') rely on structured rating data. Without it, your products are excluded from comparison answers.",
            evidence=[EvidenceItem(source_type="json_ld", url=u, detail="Product page lacks AggregateRating or Review in JSON-LD and no visible review content.") for u in product_pages_without_reviews[:3]],
            confidence=0.75,
            impact="high",
            priority="P2",
            suggested_action=ActionRecommendation(
                summary="Add AggregateRating and Review schema to product pages.",
                priority="P2",
                implementation="Collect and display user reviews. Add schema.org/AggregateRating and schema.org/Review JSON-LD to product pages.",
                verification="Verify JSON-LD contains aggregateRating with ratingValue and reviewCount.",
                effort="medium",
                expected_impact="high"
            )
        ))
    return opportunities


def _check_heading_hierarchy_opportunity(html_cache: dict, context: AuditContext) -> list:
    """Detect flat heading structure missing h2/h3 subheadings."""
    opportunities = []
    flat_pages = []
    
    for url, html in html_cache.items():
        soup = BeautifulSoup(html, 'html.parser')
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        h3_count = len(soup.find_all('h3'))
        
        text = extract_visible_text(html)
        
        # Flag pages with an H1 but no subheadings and substantial content
        if h1_count >= 1 and h2_count == 0 and h3_count == 0 and len(text) > 500:
            flat_pages.append(url)
    
    if flat_pages:
        opportunities.append(Opportunity(
            id="OPP-003",
            title="Content Hierarchy Gap: Flat Heading Structure",
            description="Pages with substantial content but no H2/H3 subheadings make it harder for AI to segment topics and extract section-specific answers.",
            evidence=[EvidenceItem(source_type="html", url=u, detail="Page has H1 but zero H2/H3 headings despite significant content length.") for u in flat_pages[:3]],
            confidence=0.7,
            impact="medium",
            priority="P3",
            suggested_action=ActionRecommendation(
                summary="Add H2/H3 subheadings to organize content into scannable sections.",
                priority="P3",
                implementation="Break long content into logical sections with descriptive H2/H3 headings. This enables AI to extract section-specific answers.",
                verification="Verify each content page has at least one H2 under the main H1.",
                effort="low",
                expected_impact="medium"
            )
        ))
    return opportunities


def _check_attribute_coverage_opportunity(html_cache: dict, context: AuditContext) -> list:
    """Detect JSON-LD with missing key attributes (description, image, brand)."""
    opportunities = []
    incomplete_schemas = []
    
    key_attributes = ['description', 'image', 'brand']
    
    for url, html in html_cache.items():
        json_ld = extract_json_ld(html)
        for block in json_ld:
            if block.get('@type') == 'Product':
                missing = [attr for attr in key_attributes if attr not in block]
                if missing:
                    incomplete_schemas.append((url, missing))
    
    if incomplete_schemas:
        evidence = [EvidenceItem(
            source_type="json_ld", 
            url=u[0], 
            detail=f"Product JSON-LD is missing: {', '.join(u[1])}. These attributes improve AI extraction confidence."
        ) for u in incomplete_schemas[:3]]
        
        opportunities.append(Opportunity(
            id="OPP-004",
            title="Incomplete Product Schema: Missing Key Attributes",
            description="Product JSON-LD exists but lacks important attributes (description, image, brand). Completing the schema increases extraction confidence and citation quality.",
            evidence=evidence,
            confidence=0.8,
            impact="medium",
            priority="P2",
            suggested_action=ActionRecommendation(
                summary="Complete Product JSON-LD with description, image, and brand.",
                priority="P2",
                implementation="Add missing attributes to existing Product schema. Use high-quality image URLs and concise descriptions.",
                verification="Validate Product JSON-LD contains name, description, image, brand, and offers.",
                effort="low",
                expected_impact="medium"
            )
        ))
    return opportunities


def _check_sameas_opportunity(html_cache: dict, context: AuditContext) -> list:
    """Detect Organization entities without sameAs links to authoritative sources."""
    opportunities = []
    
    for url, html in html_cache.items():
        json_ld = extract_json_ld(html)
        for block in json_ld:
            if block.get('@type') in ['Organization', 'Corporation', 'LocalBusiness', 'Brand']:
                same_as = block.get('sameAs', [])
                if not same_as:
                    opportunities.append(Opportunity(
                        id="OPP-005",
                        title="Add sameAs Links for Entity Authority",
                        description="Organization entity lacks sameAs links to authoritative sources (Wikipedia, LinkedIn, Wikidata). This weakens entity resolution in knowledge graphs.",
                        evidence=[EvidenceItem(source_type="json_ld", url=url, detail=f"Organization '{block.get('name', 'unknown')}' has no sameAs links to external authoritative profiles.")],
                        confidence=0.85,
                        impact="medium",
                        priority="P2",
                        suggested_action=ActionRecommendation(
                            summary="Add sameAs links pointing to Wikipedia, LinkedIn, and Wikidata.",
                            priority="P2",
                            implementation="Add sameAs array to Organization JSON-LD: ['https://en.wikipedia.org/wiki/...', 'https://www.linkedin.com/company/...', 'https://www.wikidata.org/wiki/...'].",
                            verification="Verify Organization JSON-LD contains sameAs with at least one authoritative external URL.",
                            effort="low",
                            expected_impact="medium"
                        )
                    ))
                    return opportunities  # Only emit once per site
    return opportunities


def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    """
    Proactive opportunity detection engine.
    
    Runs 5 independent detectors that look for improvement opportunities
    beyond explicit defects:
      1. Missing FAQ schema
      2. Missing comparison/review data
      3. Flat content hierarchy
      4. Incomplete product attributes
      5. Missing entity authority links (sameAs)
    """
    all_opportunities = []
    
    all_opportunities.extend(_check_faq_opportunity(html_cache, context))
    all_opportunities.extend(_check_comparison_opportunity(html_cache, context))
    all_opportunities.extend(_check_heading_hierarchy_opportunity(html_cache, context))
    all_opportunities.extend(_check_attribute_coverage_opportunity(html_cache, context))
    all_opportunities.extend(_check_sameas_opportunity(html_cache, context))
    
    context.opportunities.extend(all_opportunities)
    return context
