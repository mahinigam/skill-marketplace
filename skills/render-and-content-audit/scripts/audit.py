import sys
import os
import json
from typing import List, Tuple
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, FindingCategory
from shared.utilities.extractors import extract_visible_text


class SimulatedRenderer:
    """
    Simulated Headless Rendering (Bounded Execution).
    
    Avoids bundling Chromium binaries (<50MB constraint) by reconstructing
    what the 'rendered' text volume would be from embedded state objects
    in <script> tags (e.g., __NEXT_DATA__, window.__INITIAL_STATE__).
    
    Returns (raw_text, rendered_text) where:
      - raw_text: visible text extracted from the static HTML DOM
      - rendered_text: raw_text + text reconstructed from script state objects
    """
    @staticmethod
    def render(html: str) -> Tuple[str, str]:
        soup = BeautifulSoup(html, 'html.parser')
        
        for s in soup(["script", "style", "noscript", "meta", "link", "head"]):
            s.extract()
        raw_text = soup.get_text(separator=' ', strip=True)
        
        # Reconstruct rendered state by extracting strings from embedded JSON
        rendered_text = raw_text
        original_soup = BeautifulSoup(html, 'html.parser')
        for script in original_soup.find_all('script'):
            if script.string:
                try:
                    content = script.string.strip()
                    if content.startswith('{') or content.startswith('['):
                        data = json.loads(content)
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
                except Exception:
                    pass
                    
        return raw_text, rendered_text


class PlaywrightRenderer:
    """
    Optional Bounded Playwright Mode.
    
    When playwright is available in the environment, performs real browser
    execution within a bounded 5-second timeout. Uses the raw HTTP-fetched
    HTML as the baseline for comparison (not an empty string).
    """
    @staticmethod
    def is_available() -> bool:
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def render(url: str, raw_html: str) -> Tuple[str, str]:
        """
        Returns (raw_text, rendered_text) where raw_text comes from the
        HTTP-fetched HTML and rendered_text comes from the browser DOM.
        
        This ensures a fair comparison: both sides represent the same page,
        one without JS execution and one with.
        """
        # Extract baseline visible text from the raw HTTP response
        raw_text = extract_visible_text(raw_html)
        
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=5000)
            rendered_text = page.locator("body").inner_text()
            browser.close()
            
        return raw_text, rendered_text


def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    js_heavy_pages = []
    
    simulated_renderer = SimulatedRenderer()
    has_playwright = PlaywrightRenderer.is_available()
    
    for url, html in html_cache.items():
        if has_playwright:
            try:
                # Pass raw HTML so the baseline is extracted from HTTP content,
                # NOT an empty string. This prevents false positives.
                raw_text, rendered_text = PlaywrightRenderer.render(url, html)
            except Exception:
                # Fallback to simulated on failure (timeout, missing browser, etc.)
                raw_text, rendered_text = simulated_renderer.render(html)
        else:
            raw_text, rendered_text = simulated_renderer.render(html)
        
        raw_len = len(raw_text.strip())
        rendered_len = len(rendered_text.strip())
        
        # Only flag when raw text is thin AND rendered text is substantially larger.
        # This indicates the page relies on JS hydration to expose core facts.
        if raw_len < 500 and rendered_len > raw_len * 3:
            js_heavy_pages.append((url, raw_len, rendered_len))
                
    if js_heavy_pages:
        evidence = []
        for url, r_len, rend_len in js_heavy_pages[:5]:
            evidence.append(EvidenceItem(
                source_type="html",
                url=url,
                detail=f"Raw text: {r_len} chars. Rendered text: {rend_len} chars. Massive JS hydration dependency."
            ))
            
        findings.append(Finding(
            id="RENDER-001",
            title="Core content relies entirely on client-side rendering",
            category=FindingCategory.DISCOVERABILITY,
            type=FindingType.DEFECT,
            severity="critical", 
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
