import sys
import os
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation
from shared.utilities.extractors import extract_visible_text

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    js_heavy_pages = []
    
    for url, html in html_cache.items():
        text = extract_visible_text(html)
        # Simple heuristic: if the visible text is very short but the page size is large, it's likely a JS SPA.
        # Alternatively, if we see typical SPA mounting points.
        if len(text.strip()) < 100 and len(html) > 5000:
            if 'id="root"' in html or 'id="app"' in html:
                js_heavy_pages.append(url)
                
    if js_heavy_pages:
        findings.append(Finding(
            id="RENDER-001",
            title="Core content depends on client-side rendering",
            category="machine_readability",
            type="defect",
            severity="high",
            confidence=0.85,
            affected_pages=js_heavy_pages[:5],
            evidence=[EvidenceItem(source_type="html", url=u, detail="Initial HTML contains almost no visible text, indicating JS hydration dependency.") for u in js_heavy_pages[:5]],
            mechanism="AI bots might not execute JavaScript, leaving them with blank pages and no facts.",
            ai_impact="Important facts may be unavailable to a simple retrieval/extraction path.",
            user_impact="A visitor arriving from an AI answer may not immediately see the facts.",
            root_cause="Product template depends on client-side hydration for core content.",
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
