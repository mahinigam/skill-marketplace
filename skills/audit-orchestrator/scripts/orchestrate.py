import sys
import os
import datetime
import json
from urllib.parse import urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, AuditTarget, CrawlRecord, PageRecord, FinalAuditReport
from shared.utilities.http_client import SafeHTTPClient
from shared.utilities.crawler import SiteCrawler
from shared.utilities.scoring import summarize_audit

# Import all skills
from skills.crawlability_audit.scripts import audit as crawl_audit
from skills.render_and_content_audit.scripts import audit as render_audit
from skills.semantic_structure_audit.scripts import audit as semantic_audit
from skills.entity_resolution_audit.scripts import audit as entity_audit
from skills.freshness_and_corroboration_audit.scripts import audit as freshness_audit
from skills.answerability_audit.scripts import audit as answerability_audit
from skills.semantic_integrity_audit.scripts import audit as integrity_audit
from skills.ai_landing_context_audit.scripts import audit as landing_audit
from skills.opportunity_engine.scripts import audit as opportunity_engine

def run_orchestrator(target_url: str) -> FinalAuditReport:
    client = SafeHTTPClient()
    crawler = SiteCrawler(client)
    
    parsed = urlparse(target_url)
    domain = parsed.netloc
    
    context = AuditContext(
        target=AuditTarget(url=target_url, domain=domain),
        crawl=CrawlRecord(start_time=datetime.datetime.now(datetime.timezone.utc))
    )
    
    print(f"Starting audit for {target_url}...")
    
    # 1. Discover Pages
    discovered_urls = crawler.discover_pages(target_url, max_pages=20)
    context.crawl.sitemaps_found = crawler.sitemap_urls
    context.crawl.robots_txt_content = crawler.robots_content
    
    # 2. Fetch and Cache HTML
    html_cache = {}
    for url in discovered_urls:
        content, resp, err = client.get(url)
        if resp:
            context.crawl.pages[url] = PageRecord(
                url=url,
                status_code=resp.status_code,
                content_type=resp.headers.get("Content-Type", ""),
                size_bytes=len(content) if content else 0,
                robots_allowed=crawler.can_fetch(url),
                importance="P2" # Simplification
            )
        if content:
            html_cache[url] = content
            
    context.crawl.pages_visited = len(discovered_urls)
    
    # 3. Execute Skills
    print("Running Crawlability Audit...")
    context = crawl_audit.run_audit(context, crawler)
    
    print("Running Render & Content Audit...")
    context = render_audit.run_audit(context, html_cache)
    
    print("Running Semantic Structure Audit...")
    context = semantic_audit.run_audit(context, html_cache)
    
    print("Running Entity Resolution Audit...")
    context = entity_audit.run_audit(context, html_cache)
    
    print("Running Freshness & Corroboration Audit...")
    context = freshness_audit.run_audit(context, html_cache)
    
    print("Running Answerability Audit...")
    context = answerability_audit.run_audit(context, html_cache)
    
    print("Running Semantic Integrity Audit...")
    context = integrity_audit.run_audit(context, html_cache)
    
    print("Running AI Landing Context Audit...")
    context = landing_audit.run_audit(context, html_cache)
    
    print("Running Opportunity Engine...")
    context = opportunity_engine.run_audit(context, html_cache)
    
    client.close()
    
    # 4. Finalize
    context.crawl.end_time = datetime.datetime.now(datetime.timezone.utc)
    
    # Summarize
    summary = summarize_audit(context.findings)
    
    # Root Cause Correlation (Simple deduplication / grouping)
    root_causes = list(set([f.root_cause for f in context.findings if f.root_cause]))
    
    report = FinalAuditReport(
        site=domain,
        audited_at=context.crawl.end_time.isoformat().replace("+00:00", "Z"),
        summary=summary,
        findings=context.findings,
        opportunities=context.opportunities,
        root_causes=root_causes
    )
    
    return report

def generate_markdown_report(report: FinalAuditReport) -> str:
    md = f"# AI READINESS AUDIT\n\n"
    md += f"**Site:** {report.site}\n"
    md += f"**Audit Timestamp:** {report.audited_at}\n\n"
    
    md += f"## OVERALL READINESS: {report.summary.ai_readiness_score} / 100\n\n"
    
    md += f"### SUMMARY\n"
    md += f"- Critical: {report.summary.critical}\n"
    md += f"- High: {report.summary.high}\n"
    md += f"- Medium: {report.summary.medium}\n"
    md += f"- Low: {report.summary.low}\n\n"
    
    if report.root_causes:
        md += "## ROOT CAUSES\n"
        for rc in report.root_causes:
            md += f"- {rc}\n"
        md += "\n"
        
    md += "## DETAILED FINDINGS\n\n"
    for f in sorted(report.findings, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.severity, 4)):
        md += f"### {f.title}\n"
        md += f"**Severity:** {f.severity.upper()} | **Confidence:** {f.confidence}\n\n"
        
        md += "**Evidence:**\n"
        for ev in f.evidence:
            md += f"- {ev.detail}\n"
        md += "\n"
        
        if f.mechanism: md += f"**Mechanism:** {f.mechanism}\n\n"
        if f.ai_impact: md += f"**AI Impact:** {f.ai_impact}\n\n"
        if f.user_impact: md += f"**User Impact:** {f.user_impact}\n\n"
        
        if f.suggested_action:
            md += f"**ACTION:** {f.suggested_action.summary}\n\n"
            md += f"**Implementation:** {f.suggested_action.implementation}\n\n"
            md += f"**Verification:** {f.suggested_action.verification}\n\n"
            md += f"**Priority:** {f.suggested_action.priority}\n\n"
            
        md += "---\n\n"
        
    md += "## OPPORTUNITIES\n\n"
    for opp in report.opportunities:
        md += f"### {opp.title}\n"
        md += f"{opp.description}\n\n"
        md += f"**ACTION:** {opp.suggested_action.summary}\n\n"
        md += "---\n\n"
        
    return md
