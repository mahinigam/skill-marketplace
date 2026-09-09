import sys
import os
import re
from typing import List, Dict, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_visible_text


class ExpectedFact:
    def __init__(self, key: str, extractors: List[str]):
        self.key = key
        self.extractors = extractors


class SyntheticQuestion:
    def __init__(self, text: str, intent: str, expected_facts: List[ExpectedFact],
                 url_triggers: Optional[List[str]] = None, text_triggers: Optional[List[str]] = None,
                 weight: float = 1.0):
        """
        A synthetic question that an AI might need to answer from this page.
        
        url_triggers: URL substrings that suggest this question is relevant.
        text_triggers: Visible text substrings that suggest this question is relevant.
        weight: How important this question is for the overall score (higher = more impact).
               Primary purchase/identity intents should be weighted higher.
        """
        self.text = text
        self.intent = intent
        self.expected_facts = expected_facts
        self.url_triggers = url_triggers or []
        self.text_triggers = text_triggers or []
        self.weight = weight

    def is_relevant(self, url: str, text: str) -> bool:
        """Check if this question is relevant to the given page."""
        url_lower = url.lower()
        text_lower = text.lower()
        
        for trigger in self.url_triggers:
            if trigger in url_lower:
                return True
        for trigger in self.text_triggers:
            if trigger in text_lower:
                return True
        return False


# ---------------------------------------------------------------------------
# Comprehensive Question Library (8 intent categories)
# ---------------------------------------------------------------------------

QUESTION_LIBRARY = [
    SyntheticQuestion(
        text="What is the price and is it in stock?",
        intent="purchase_decision",
        expected_facts=[
            ExpectedFact("price", [r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*', r'(?:usd|eur|gbp|inr|cad|aud)\s*\d+']),
            ExpectedFact("availability", [r'in stock', r'out of stock', r'available', r'sold out', r'add to cart', r'buy now'])
        ],
        url_triggers=["product", "item", "buy", "shop", "store"],
        text_triggers=["add to cart", "buy now", "price", "add to bag"],
        weight=3.0  # Primary purchase intent is the most critical question
    ),
    SyntheticQuestion(
        text="What is this product or company?",
        intent="identity",
        expected_facts=[
            ExpectedFact("name", [r'^\s*(\S.{3,80})$']),
            ExpectedFact("description", [r'(?:about|description|overview|who we are)\s*[:\-]?\s*(.{20,})'])
        ],
        url_triggers=["about", "company", "brand"],
        text_triggers=["about us", "who we are", "our mission", "our story", "overview"],
        weight=2.0  # Identity is a key baseline question
    ),
    SyntheticQuestion(
        text="What are the technical specifications?",
        intent="specification",
        expected_facts=[
            ExpectedFact("dimensions", [r'(?:dimensions?|size)\s*[:\-]?\s*([\d\.]+\s*[xX×]\s*[\d\.]+)', r'\b(\d+\.?\d*)\s*(?:mm|cm|inches)\b']),
            ExpectedFact("weight", [r'(?:weight)\s*[:\-]?\s*([\d\.]+\s*(?:kg|g|lb|oz|pounds?))\b']),
            ExpectedFact("material", [r'(?:material|made (?:of|from|with))\s*[:\-]?\s*(\w[\w\s,]+)'])
        ],
        url_triggers=["spec", "detail", "technical"],
        text_triggers=["specifications", "dimensions", "weight", "material", "tech specs"]
    ),
    SyntheticQuestion(
        text="Is this trustworthy? What do others say?",
        intent="trust",
        expected_facts=[
            ExpectedFact("rating", [r'(\d[\.\d]*)\s*(?:out of|/)\s*5', r'(\d[\.\d]*)\s*stars?']),
            ExpectedFact("review_count", [r'(\d[\d,]*)\s*(?:reviews?|ratings?|customers?)', r'based on\s*(\d[\d,]*)\s*(?:reviews?|ratings?)'])
        ],
        url_triggers=["review", "testimonial"],
        text_triggers=["reviews", "rating", "stars", "customers say", "testimonial"]
    ),
    SyntheticQuestion(
        text="Where is this located and how can I contact them?",
        intent="location",
        expected_facts=[
            ExpectedFact("address", [r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|blvd|drive|dr|lane|ln)\b', r'(?:address)\s*[:\-]?\s*(.{10,})']),
            ExpectedFact("phone", [r'(?:\+?\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}']),
            ExpectedFact("email", [r'[\w\.\+\-]+@[\w\-]+\.[\w\.\-]+'])
        ],
        url_triggers=["contact", "about", "location", "store", "find-us"],
        text_triggers=["contact us", "get in touch", "our address", "call us", "email us"]
    ),
    SyntheticQuestion(
        text="Is this information current?",
        intent="freshness",
        expected_facts=[
            ExpectedFact("date", [r'(?:updated|modified|published|posted)\s*(?:on|:)?\s*(\w+ \d{1,2},? \d{4})', r'20\d{2}[-/]\d{2}[-/]\d{2}']),
            ExpectedFact("version", [r'(?:version|v)\s*\.?\s*(\d+[\.\d]*)'])
        ],
        url_triggers=["blog", "article", "news", "post", "docs", "documentation"],
        text_triggers=["published", "updated", "last modified", "posted on", "version"]
    ),
    SyntheticQuestion(
        text="What is this used for?",
        intent="use_case",
        expected_facts=[
            ExpectedFact("description", [r'(?:use|used for|designed for|ideal for|perfect for)\s*[:\-]?\s*(.{15,})']),
            ExpectedFact("features", [r'(?:features?|benefits?|highlights?)\s*[:\-]?\s*(.{10,})']),
            ExpectedFact("category", [r'(?:category|type|kind)\s*[:\-]?\s*(\w[\w\s]+)'])
        ],
        url_triggers=["service", "solution"],
        text_triggers=["features", "benefits", "designed for", "ideal for", "use case"]
    ),
    SyntheticQuestion(
        text="How does this compare to alternatives?",
        intent="comparison",
        expected_facts=[
            ExpectedFact("rating", [r'(\d[\.\d]*)\s*(?:out of|/)\s*5', r'(\d[\.\d]*)\s*stars?']),
            ExpectedFact("review_count", [r'(\d[\d,]*)\s*(?:reviews?|ratings?)']),
            ExpectedFact("price", [r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*'])
        ],
        url_triggers=["compare", "vs", "alternative"],
        text_triggers=["compare", "versus", "alternative", "competitor"]
    ),
]


def retrieve_fact(html_text: str, fact: ExpectedFact) -> List[str]:
    """Attempt to extract a fact from visible text using regex extractors."""
    results = []
    for regex in fact.extractors:
        matches = re.findall(regex, html_text, re.IGNORECASE)
        results.extend([str(m) for m in matches])
    return list(set(results))


def evaluate_answerability(html_text: str, questions: List[SyntheticQuestion]) -> float:
    """
    Score how well a page can answer a set of synthetic questions.
    
    Returns a score between 0.0 and 1.0:
      - 1.0 = all expected facts found unambiguously
      - 0.5 = facts found but ambiguous (multiple matches)
      - 0.0 = expected facts missing entirely
    """
    weighted_sum = 0.0
    weight_total = 0.0
    for q in questions:
        fact_scores = []
        for fact in q.expected_facts:
            retrieved = retrieve_fact(html_text, fact)
            if len(retrieved) == 1:
                fact_scores.append(1.0)  # Unambiguous coverage
            elif len(retrieved) > 1:
                fact_scores.append(0.5)  # Ambiguous coverage
            else:
                fact_scores.append(0.0)  # No coverage
                
        # Question score is the average of its expected facts
        if fact_scores:
            q_score = sum(fact_scores) / len(fact_scores)
            weighted_sum += q_score * q.weight
            weight_total += q.weight
            
    return weighted_sum / weight_total if weight_total > 0 else 1.0


def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    unanswerable_pages = []
    
    for url, html in html_cache.items():
        text = extract_visible_text(html)
        
        # Select relevant questions for this page based on URL and content triggers
        relevant_questions = [q for q in QUESTION_LIBRARY if q.is_relevant(url, text)]
        
        if not relevant_questions:
            continue
            
        score = evaluate_answerability(text, relevant_questions)
        if score <= 0.5:
            failed_intents = [q.intent for q in relevant_questions]
            unanswerable_pages.append((url, score, failed_intents))
                
    if unanswerable_pages:
        evidence = [EvidenceItem(
            source_type="html", 
            url=u[0], 
            detail=f"Answerability score: {u[1]:.2f}. Failed intents: {', '.join(u[2])}. Expected facts could not be unambiguously extracted."
        ) for u in unanswerable_pages[:5]]
        
        findings.append(Finding(
            id="ANS-001",
            title="Poor Answerability for High-Intent Queries",
            category=FindingCategory.ENGAGEMENT,
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.85,
            affected_pages=[u[0] for u in unanswerable_pages],
            evidence=evidence,
            mechanism="AI constructs answers by retrieving specific expected facts. If extraction fails or yields ambiguous results, it drops the citation.",
            ai_impact="AI states it doesn't know the price or specifications, refusing to confidently recommend the product.",
            suggested_action=ActionRecommendation(
                summary="Ensure facts can unambiguously answer common user questions.",
                priority="P1",
                implementation="Add explicit text blocks for price, stock, specs, and contact info. Avoid hiding facts in images or non-standard formats.",
                verification="Test if a generic LLM can extract expected facts purely from the page's raw text.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
