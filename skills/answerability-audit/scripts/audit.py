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
    def __init__(self, text: str, intent: str, expected_facts: List[ExpectedFact]):
        self.text = text
        self.intent = intent
        self.expected_facts = expected_facts

def retrieve_fact(html_text: str, fact: ExpectedFact) -> List[str]:
    results = []
    for regex in fact.extractors:
        matches = re.findall(regex, html_text, re.IGNORECASE)
        results.extend(matches)
    return list(set(results))

def evaluate_answerability(html_text: str, questions: List[SyntheticQuestion]) -> float:
    scores = []
    for q in questions:
        fact_scores = []
        for fact in q.expected_facts:
            retrieved = retrieve_fact(html_text, fact)
            if len(retrieved) == 1:
                fact_scores.append(1.0) # Unambiguous coverage
            elif len(retrieved) > 1:
                fact_scores.append(0.5) # Ambiguous coverage
            else:
                fact_scores.append(0.0) # No coverage
                
        # Question score is the average of its expected facts
        if fact_scores:
            scores.append(sum(fact_scores) / len(fact_scores))
            
    return sum(scores) / len(scores) if scores else 1.0

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    product_questions = [
        SyntheticQuestion(
            text="What is the price and is it in stock?", 
            intent="purchase_decision", 
            expected_facts=[
                ExpectedFact("price", [r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*', r'(?:usd|eur|gbp|inr|cad|aud)\s*\d+']),
                ExpectedFact("availability", [r'in stock', r'out of stock', r'available', r'sold out'])
            ]
        )
    ]
    
    unanswerable_pages = []
    
    for url, html in html_cache.items():
        text = extract_visible_text(html)
        
        if 'product' in url.lower() or 'buy' in text.lower() or 'add to cart' in text.lower():
            score = evaluate_answerability(text, product_questions)
            if score < 0.5:
                unanswerable_pages.append((url, score))
                
    if unanswerable_pages:
        evidence = [EvidenceItem(
            source_type="html", 
            url=u[0], 
            detail=f"Answerability score: {u[1]:.2f}. Failed to retrieve expected facts (price, availability) to answer synthetic query."
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
                implementation="Add explicit text blocks for price and stock. Avoid hiding facts in images or non-standard formats.",
                verification="Test if a generic LLM can extract expected facts purely from the page's raw text.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
