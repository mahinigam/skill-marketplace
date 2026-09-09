import sys
import os
from typing import List

# Ensure we can import shared
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingCategory
from shared.utilities.crawler import SiteCrawler

def run_audit(context: AuditContext, crawler: SiteCrawler) -> AuditContext:
    findings = []
    
    # 1. Robots.txt Analysis
    if not crawler.robots_content:
        findings.append(Finding(
            id="CRAWL-001",
            title="Missing robots.txt",
            category=FindingCategory.DISCOVERABILITY,
            type="risk",
            severity="medium",
            confidence=0.9,
            evidence=[EvidenceItem(source_type="http", url=context.target.url, detail="robots.txt returned 404 or was unreachable.")],
            mechanism="Crawlers may rely on default behaviors or miss sitemap hints if robots.txt is missing.",
            suggested_action=ActionRecommendation(
                summary="Create a basic robots.txt file.",
                priority="P2",
                implementation="Add a robots.txt at the root domain that specifies allowed paths and the sitemap location.",
                verification="Fetch /robots.txt and confirm a 200 OK status.",
                effort="low",
                expected_impact="low"
            )
        ))
    
    # 2. Sitemap Analysis
    if not crawler.sitemap_urls:
        findings.append(Finding(
            id="CRAWL-002",
            title="Missing Sitemap",
            category=FindingCategory.DISCOVERABILITY,
            type="risk",
            severity="high",
            confidence=0.95,
            evidence=[EvidenceItem(source_type="discovery", url=context.target.url, detail="No sitemaps declared in robots.txt and /sitemap.xml not found.")],
            mechanism="AI systems rely on sitemaps to discover new and updated content efficiently.",
            suggested_action=ActionRecommendation(
                summary="Generate and expose an XML sitemap.",
                priority="P1",
                implementation="Create an XML sitemap of all canonical URLs and reference it in robots.txt.",
                verification="Check if /sitemap.xml exists and contains valid URLs.",
                effort="low",
                expected_impact="medium"
            )
        ))
        
    # 3. HTTP Errors Analysis
    error_urls = []
    for url, page in context.crawl.pages.items():
        if page.status_code >= 400:
            error_urls.append(url)
            
    if error_urls:
        findings.append(Finding(
            id="CRAWL-003",
            title="HTTP Errors on Sampled Pages",
            category=FindingCategory.DISCOVERABILITY,
            type="defect",
            severity="high",
            confidence=1.0,
            affected_pages=error_urls[:5],
            evidence=[EvidenceItem(source_type="http", url=u, detail=f"Returned HTTP {context.crawl.pages[u].status_code}") for u in error_urls[:5]],
            mechanism="HTTP errors on important pages prevent crawlers and AI assistants from indexing that content at all.",
            suggested_action=ActionRecommendation(
                summary="Fix HTTP errors or implement proper redirects.",
                priority="P0",
                implementation="Ensure important content returns 200 OK. Use 301 redirects for moved content.",
                verification="Fetch the URLs and verify 200 OK.",
                effort="medium",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
