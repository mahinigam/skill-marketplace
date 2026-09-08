import sys
import os
import json
from typing import List
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType

class SimulatedRenderer:
    """
    To adhere to the < 50MB constraint, this avoids Chromium binaries.
    It simulates headless execution by parsing state objects in <script> tags
    (e.g., __NEXT_DATA__, window.__INITIAL_STATE__, or raw JSON payloads)
    to estimate what the 'rendered' text volume would be.
    """
    @staticmethod
    def render(html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Raw text extraction without scripts
        for s in soup(["script", "style", "noscript", "meta", "link", "head"]):
            s.extract()
        raw_text = soup.get_text(separator=' ', strip=True)
        
        # Now simulate execution by finding embedded state
        rendered_text = raw_text
        original_soup = BeautifulSoup(html, 'html.parser')
        for script in original_soup.find_all('script'):
            if script.string:
                try:
                    # Very naive extraction of large JSON blobs inside scripts
                    # Real headless execution would do this perfectly
                    content = script.string.strip()
                    if content.startswith('{') or content.startswith('['):
                        data = json.loads(content)
                        # Extract all string values from the JSON dump
                        def extract_strings(obj):
                            strings = []
                            if isinstance(obj, dict):
                                for v in obj.values():
                                    strings.extend(extract_strings(v))
                            elif isinstance(obj, list):
                                for item in obj:
                                    strings.extend(extract_strings(item))
                            elif isinstance(obj, str):
                                strings.append(obj)
                            return strings
                        
                        extracted = " ".join(extract_strings(data))
                        rendered_text += " " + extracted
                except:
                    pass
                    
        return raw_text, rendered_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    js_heavy_pages = []
    
    renderer = SimulatedRenderer()
    
    for url, html in html_cache.items():
        raw_text, rendered_text = renderer.render(html)
        
        raw_len = len(raw_text.strip())
        rendered_len = len(rendered_text.strip())
        
        if raw_len < 500 and rendered_len > raw_len * 3:
            js_heavy_pages.append((url, raw_len, rendered_len))
                
    if js_heavy_pages:
        evidence = []
        for url, r_len, rend_len in js_heavy_pages[:5]:
            evidence.append(EvidenceItem(
                source_type="html",
                url=url,
                detail=f"Raw text: {r_len} chars. Simulated rendered text: {rend_len} chars. Massive JS hydration dependency."
            ))
            
        findings.append(Finding(
            id="RENDER-001",
            title="Core content relies entirely on client-side rendering",
            category="Discoverability",
            type=FindingType.DEFECT,
            severity="critical", # 90+ mapping
            confidence=0.9,
            affected_pages=[u[0] for u in js_heavy_pages],
            evidence=evidence,
            mechanism="AI bots might not execute JavaScript (or execute it unreliably), leaving them with blank pages and no facts.",
            ai_impact="Important facts (pricing, availability) may be entirely invisible to simple AI retrieval paths.",
            user_impact="A visitor arriving from an AI answer may not immediately see the facts.",
            suggested_action=ActionRecommendation(
                summary="Implement Server-Side Rendering (SSR) or dynamic rendering.",
                priority="P0",
                implementation="Expose core facts in crawlable HTML so JS execution is not required.",
                verification="Disable JS in browser and ensure core content is visible.",
                effort="high",
                expected_impact="high"
            )
        ))
        
    context.findings.extend(findings)
    return context
