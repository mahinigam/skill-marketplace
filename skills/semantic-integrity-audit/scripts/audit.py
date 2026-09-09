import sys
import os
import re
from bs4 import BeautifulSoup, Tag

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_visible_text


# Semantic containers that establish clear content ownership
PRIMARY_CONTAINERS = {"main", "article"}
AUXILIARY_CONTAINERS = {"aside", "nav", "footer", "header"}
BOUNDARY_CONTAINERS = PRIMARY_CONTAINERS | AUXILIARY_CONTAINERS | {"section"}


def _find_owning_container(element: Tag) -> str:
    """
    Walk up the DOM tree from an element to find its nearest semantic container.
    Returns the container tag name, or 'unowned' if no semantic boundary exists.
    """
    current = element.parent
    while current and current.name:
        if current.name in BOUNDARY_CONTAINERS:
            return current.name
        current = current.parent
    return "unowned"


def _classify_price_ownership(html: str) -> dict:
    """
    For each price found in the DOM, determine which semantic container owns it.
    
    Returns a dict:
      {
        "primary": [(price_text, owner_tag), ...],    # prices in <main>/<article>
        "auxiliary": [(price_text, owner_tag), ...],   # prices in <aside>/<nav>/<footer>
        "orphaned": [(price_text, owner_tag), ...],    # prices with no semantic owner
      }
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script/style before searching for prices
    for tag in soup(["script", "style"]):
        tag.decompose()
    
    classification = {"primary": [], "auxiliary": [], "orphaned": []}
    
    # Find all text nodes containing price patterns
    price_pattern = re.compile(r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*')
    
    for text_node in soup.find_all(string=price_pattern):
        prices = price_pattern.findall(text_node)
        parent_tag = text_node.parent
        if not parent_tag or not isinstance(parent_tag, Tag):
            continue
            
        owner = _find_owning_container(parent_tag)
        
        for price in prices:
            if owner in PRIMARY_CONTAINERS:
                classification["primary"].append((price.strip(), owner))
            elif owner in AUXILIARY_CONTAINERS:
                classification["auxiliary"].append((price.strip(), owner))
            else:
                classification["orphaned"].append((price.strip(), owner))
    
    return classification


def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    boundary_failures = []
    
    for url, html in html_cache.items():
        # Only analyze product/detail pages where attribute ownership matters
        if not ('product' in url.lower() or 'detail' in url.lower() or 'item' in url.lower()):
            continue
        
        ownership = _classify_price_ownership(html)
        
        orphaned_prices = ownership["orphaned"]
        auxiliary_prices = ownership["auxiliary"]
        primary_prices = ownership["primary"]
        
        # Condition 1: Orphaned prices on a product page → semantic boundary failure
        # These are prices living in undifferentiated <div> soup with no container.
        if len(orphaned_prices) > 1:
            # Check for cart/total signals that would make these legitimate global prices
            text = extract_visible_text(html)
            cart_signals = len(re.findall(r'(cart|total|subtotal|checkout)', text, re.IGNORECASE))
            
            # Only flag if these aren't cart-related
            if cart_signals < 2:
                all_prices = [p[0] for p in orphaned_prices]
                boundary_failures.append((
                    url, 
                    all_prices,
                    "orphaned",
                    f"{len(orphaned_prices)} prices exist outside any semantic container (<main>, <article>, <aside>)"
                ))
        
        # Condition 2: Auxiliary prices bleeding into a page that also has primary prices
        # This indicates <aside> content (related products) might confuse extraction
        if primary_prices and auxiliary_prices:
            primary_values = set(p[0] for p in primary_prices)
            auxiliary_values = set(p[0] for p in auxiliary_prices)
            
            # Only flag if auxiliary prices differ from primary (not cart mirrors)
            bleeding_prices = auxiliary_values - primary_values
            if len(bleeding_prices) >= 2:
                # Check if auxiliary content contains cart/checkout signals
                # Cart totals (subtotal, tax, total) are legitimate and expected to differ
                text = extract_visible_text(html)
                cart_signals = len(re.findall(r'(cart|total|subtotal|checkout|tax|shipping)', text, re.IGNORECASE))
                
                if cart_signals < 2:
                    boundary_failures.append((
                        url,
                        list(bleeding_prices),
                        "bleed",
                        f"{len(bleeding_prices)} distinct prices from <aside>/<nav> differ from the primary product price(s)"
                    ))
                
    if boundary_failures:
        evidence = [EvidenceItem(
            source_type="html", 
            url=u[0], 
            detail=f"[{u[2]}] {u[3]}. Prices: {', '.join(u[1][:4])}"
        ) for u in boundary_failures[:5]]
        
        findings.append(Finding(
            id="SEM-001",
            title="Semantic Boundary Failure: Content Bleed",
            category=FindingCategory.SEMANTICS,
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.85,
            affected_pages=[u[0] for u in boundary_failures],
            evidence=evidence,
            mechanism="Without clear semantic tags (<main>, <aside>), AI scrapers ingest headers, sidebars (related products), and footers as primary content.",
            ai_impact="AI quotes the price of a 'related product' or 'cart total' instead of the actual product requested.",
            suggested_action=ActionRecommendation(
                summary="Enclose core content in <main> and auxiliary content in <aside>.",
                priority="P1",
                implementation="Wrap related products, sidebars, and nav elements in <aside> or <nav> to exclude them from the primary content node.",
                verification="Parse page with a basic article extractor (like Readability) and ensure only the main product remains.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
