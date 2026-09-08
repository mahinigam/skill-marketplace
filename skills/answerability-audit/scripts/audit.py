import sys
import os
import re
from typing import List, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType
from shared.utilities.extractors import extract_visible_text

class SyntheticQuestion:
    def __init__(self, text: str, intent: str, extractors: List[str]):
        self.text = text
        self.intent = intent
        self.extractors = extractors

def evaluate_answerability(html_text: str, questions: List[SyntheticQuestion]) -> float:
    scores = []
    for q in questions:
        matches = 0
        for regex in q.extractors:
            matches += len(re.findall(regex, html_text, re.IGNORECASE))
        
        if matches == 1:
            scores.append(1.0) # Unambiguous coverage
        elif matches > 1:
            scores.append(0.5) # Ambiguous coverage (multiple potential answers)
        else:
            scores.append(0.0) # No coverage
            
    return sum(scores) / len(scores) if scores else 1.0

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    product_questions = [
        SyntheticQuestion("What is the price?", "price", [r'[\$\€\£\₹\¥]\s*\d+[\.,]?\d*', r'(?:usd|eur|gbp|inr|cad|aud)\s*\d+']),
        SyntheticQuestion("Is it in stock?", "availability", [r'in stock', r'out of stock', r'available', r'sold out']),
        SyntheticQuestion("What is the weight/size?", "dimensions", [r'\d+\s*(?:kg|lbs|oz|cm|mm|inches)'])
    ]
    
    unanswerable_pages = []
    
    for url, html in html_cache.items():
        text = extract_visible_text(html)
        
        # Determine page type
        if 'product' in url.lower() or 'buy' in text.lower() or 'add to cart' in text.lower():
            score = evaluate_answerability(text, product_questions)
            if score < 0.5:
                unanswerable_pages.append((url, score))
                
    if unanswerable_pages:
        evidence = [EvidenceItem(
            source_type="html", 
            url=u[0], 
            detail=f"Answerability score: {u[1]:.2f}. Failed to unambiguously answer synthesized product questions (price, availability, dimensions)."
        ) for u in unanswerable_pages[:5]]
        
        findings.append(Finding(
            id="ANS-001",
            title="Poor Unstructured Answerability for High-Intent Queries",
            category="Engagement",
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.85,
            affected_pages=[u[0] for u in unanswerable_pages],
            evidence=evidence,
            mechanism="AI systems extract answers from raw text. If the text lacks unambiguous factual indicators (e.g. standard currency, explicit stock status), the AI drops the citation.",
            ai_impact="AI states it doesn't know the price or specifications, refusing to confidently recommend the product.",
            suggested_action=ActionRecommendation(
                summary="Ensure facts can unambiguously answer common user questions.",
                priority="P1",
                implementation="Add explicit text blocks for price, stock, and specs. Avoid hiding facts in images or non-standard formats (e.g. 'Five thousand rupees' instead of '₹5,000').",
                verification="Test if a generic LLM can extract price, weight, and stock status purely from the page's raw text.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
