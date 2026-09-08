import sys
import os
import datetime
import json
import importlib
from urllib.parse import urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, AuditTarget, CrawlRecord, PageRecord, FinalAuditReport
from shared.utilities.http_client import SafeHTTPClient
from shared.utilities.crawler import SiteCrawler
from shared.utilities.scoring import fuse_findings, correlate_root_causes, calculate_readiness_score

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
    
    # 1. Discover Pages using PageImportance model
    discovered_urls = crawler.discover_pages(target_url, max_pages=20)
    context.crawl.sitemap_urls = crawler.sitemap_urls
    
    # 2. Fetch and Cache HTML
    print(f"Fetching {len(discovered_urls)} discovered pages...")
    for url in discovered_urls:
        content, resp, err = client.get(url)
        if resp:
            context.crawl.pages[url] = PageRecord(
                url=url,
                status_code=resp.status_code,
                content_type=resp.headers.get("Content-Type", ""),
                size_bytes=len(content) if content else 0,
                robots_allowed=crawler.can_fetch(url)
            )
        if content:
            context.html_pages[url] = content
            
    context.crawl.pages_crawled = len(discovered_urls)
    
    # 3. Dynamic Plugin execution based on marketplace.json
    market_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../marketplace.json'))
    with open(market_path, 'r') as f:
        marketplace_data = json.load(f)
        
    skills_to_run = []
    for skill in marketplace_data.get('skills', []):
        if not skill.get('entrypoint', False):
            # Formulate the module path: 'skills.skill-name.scripts.audit'
            module_name = f"{skill['path'].replace('/', '.')}.scripts.audit"
            skills_to_run.append((skill['id'], module_name))
            
    # Execute skills sequentially, passing context
    for skill_id, module_name in skills_to_run:
        print(f"Running Plugin Adapter: {skill_id}...")
        try:
            skill_module = importlib.import_module(module_name)
            # Some skills expect crawler (like crawlability), others expect html_cache
            # For simplicity, we just pass context and html_cache. Crawlability uses crawler.
            if skill_id == "crawlability-audit":
                context = skill_module.run_audit(context, crawler)
            else:
                context = skill_module.run_audit(context, context.html_pages)
        except Exception as e:
            print(f"Error executing skill {skill_id}: {e}")
    
    client.close()
    
    # 4. Finding Fusion & Root Cause Correlation
    print("Fusing findings and correlating root causes...")
    context.findings = fuse_findings(context.findings)
    context.findings, context.root_causes = correlate_root_causes(context.findings)
    
    # 5. Dimension-based Scoring
    context.crawl.end_time = datetime.datetime.now(datetime.timezone.utc)
    score = calculate_readiness_score(context.findings)
    
    summary = {
        "total_findings": len(context.findings),
        "critical": sum(1 for f in context.findings if f.severity == "critical"),
        "high": sum(1 for f in context.findings if f.severity == "high"),
        "medium": sum(1 for f in context.findings if f.severity == "medium"),
        "low": sum(1 for f in context.findings if f.severity == "low")
    }
    
    report = FinalAuditReport(
        site=domain,
        audited_at=context.crawl.end_time.isoformat().replace("+00:00", "Z"),
        score=score,
        summary=summary,
        findings=context.findings,
        opportunities=context.opportunities,
        root_causes=context.root_causes
    )
    
    return report

def generate_markdown_report(report: FinalAuditReport) -> str:
    md = f"# AI READINESS AUDIT\n\n"
    md += f"**Site:** {report.site}\n"
    md += f"**Audit Timestamp:** {report.audited_at}\n\n"
    
    md += f"## OVERALL READINESS: {report.score.total} / 100\n"
    md += f"- Discoverability: {report.score.discoverability}\n"
    md += f"- Semantics: {report.score.semantics}\n"
    md += f"- Engagement: {report.score.engagement}\n\n"
    
    md += f"### SUMMARY\n"
    md += f"- Critical: {report.summary['critical']}\n"
    md += f"- High: {report.summary['high']}\n"
    md += f"- Medium: {report.summary['medium']}\n"
    md += f"- Low: {report.summary['low']}\n\n"
    
    if report.root_causes:
        md += "## ROOT CAUSES\n"
        for rc in report.root_causes:
            md += f"### {rc.title}\n"
            md += f"{rc.description}\n"
            md += f"Contributing Findings: {', '.join(rc.contributing_findings)}\n\n"
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
        if getattr(f, 'ai_impact', None): md += f"**AI Impact:** {f.ai_impact}\n\n"
        if getattr(f, 'user_impact', None): md += f"**User Impact:** {f.user_impact}\n\n"
        
        if getattr(f, 'suggested_action', None):
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
