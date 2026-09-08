import sys
import os
import unittest
import json
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.models.models import AuditContext, AuditTarget, CrawlRecord
import importlib

crawl_audit = importlib.import_module("skills.crawlability-audit.scripts.audit")
render_audit = importlib.import_module("skills.render-and-content-audit.scripts.audit")
semantic_audit = importlib.import_module("skills.semantic-structure-audit.scripts.audit")
entity_audit = importlib.import_module("skills.entity-resolution-audit.scripts.audit")
freshness_audit = importlib.import_module("skills.freshness-and-corroboration-audit.scripts.audit")
answerability_audit = importlib.import_module("skills.answerability-audit.scripts.audit")
integrity_audit = importlib.import_module("skills.semantic-integrity-audit.scripts.audit")
landing_audit = importlib.import_module("skills.ai-landing-context-audit.scripts.audit")
opportunity_engine = importlib.import_module("skills.opportunity-engine.scripts.audit")
from shared.utilities.crawler import SiteCrawler

# Mock the HTTP client
class MockHTTPClient:
    def __init__(self, responses):
        self.responses = responses
        self.user_agent = "MockBot"

    def get(self, url):
        if url in self.responses:
            return self.responses[url], type('obj', (object,), {'status_code': 200, 'headers': {}})(), None
        return None, type('obj', (object,), {'status_code': 404, 'headers': {}})(), "Not Found"
    
    def close(self):
        pass

class TestAgentSkillMarketplace(unittest.TestCase):
    
    def setUp(self):
        self.base_context = lambda target_url: AuditContext(
            target=AuditTarget(url=target_url, domain=target_url.split("//")[1]),
            crawl=CrawlRecord(start_time=datetime.now(timezone.utc))
        )

    def test_site_01_robots_blocks(self):
        # site_01: robots blocks important content
        url = "https://site01.com"
        responses = {
            f"{url}/robots.txt": "User-agent: *\nDisallow: /products/\nSitemap: https://site01.com/sitemap.xml\n",
            f"{url}/sitemap.xml": "<urlset><loc>https://site01.com/products/1</loc></urlset>"
        }
        client = MockHTTPClient(responses)
        crawler = SiteCrawler(client)
        crawler.fetch_robots_txt(url)
        context = self.base_context(url)
        
        # Test crawlability
        context = crawl_audit.run_audit(context, crawler)
        
        # Check if robots issue was found. The crawler wouldn't fetch disallowed URLs.
        # The specific finding depends on our implementation, but it should at least discover sitemap.
        self.assertTrue(len(crawler.sitemap_urls) > 0)
        self.assertFalse(crawler.can_fetch(f"{url}/products/1"))

    def test_site_02_js_only_content(self):
        # site_02: JS-only important content
        url = "https://site02.com/product/1"
        padding = "<!-- " + "x" * 6000 + " -->"
        html = f"<html><body><div id=\"root\"></div>{padding}</body></html>"
        
        context = self.base_context(url)
        context = render_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("RENDER-001", findings)

    def test_site_03_missing_structured_data(self):
        # site_03: missing structured data
        url = "https://site03.com/product/1"
        html = """<html><body><h1>Awesome Product</h1><p>Buy now</p></body></html>"""
        
        context = self.base_context(url)
        context = semantic_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("SEM-001", findings)

    def test_site_05_entity_ambiguity(self):
        # site_05: entity ambiguity
        url = "https://site05.com/about"
        html = """
        <html>
        <head><title>A | B | C - D</title></head>
        <body>
        <script type="application/ld+json">
        [
            {"@type": "Organization", "name": "E"},
            {"@type": "Brand", "name": "F"},
            {"@type": "Brand", "name": "G"}
        ]
        </script>
        </body></html>
        """
        context = self.base_context(url)
        context = entity_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("ENT-001", findings)

    def test_site_06_stale_information(self):
        # site_06: stale information (conflicting prices)
        url = "https://site06.com/product"
        html = """
        <html><body>
        <script type="application/ld+json">
        [
          {"@type": "Product", "name": "P1", "offers": {"price": "10.00"}},
          {"@type": "Offer", "price": "15.00"}
        ]
        </script>
        </body></html>
        """
        context = self.base_context(url)
        context = freshness_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("FRESH-001", findings)
        
    def test_site_07_answerability(self):
        # site_07: unanswerable product page
        url = "https://site07.com/product/xyz"
        html = """<html><body><h1>Cool Product</h1><button>Add to cart</button></body></html>"""
        context = self.base_context(url)
        context = answerability_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("ANS-001", findings)

    def test_site_09_semantic_integrity(self):
        # site_09: cross-product attribute contamination
        url = "https://site09.com/category"
        html = """
        <html><body>
        <script type="application/ld+json">
        [
          {"@type": "Product", "name": "P1"},
          {"@type": "Product", "name": "P2"},
          {"@type": "Product", "name": "P3"},
          {"@type": "Product", "name": "P4"}
        ]
        </script>
        </body></html>
        """
        context = self.base_context(url)
        context = integrity_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("INTEGRITY-001", findings)

    def test_site_10_healthy_site(self):
        # site_10: healthy site with no major defects
        url = "https://site10.com/product"
        html = """
        <html>
        <head><title>Super Widget - WidgetCo</title></head>
        <body>
        <h1>Super Widget</h1>
        <p>This is a great widget. Price: $99.99</p>
        <script type="application/ld+json">
        [
          {"@type": "Product", "name": "Super Widget", "offers": {"price": "99.99"}},
          {"@type": "FAQPage", "mainEntity": []}
        ]
        </script>
        </body></html>
        """
        context = self.base_context(url)
        context = render_audit.run_audit(context, {url: html})
        context = semantic_audit.run_audit(context, {url: html})
        context = entity_audit.run_audit(context, {url: html})
        context = freshness_audit.run_audit(context, {url: html})
        context = answerability_audit.run_audit(context, {url: html})
        context = integrity_audit.run_audit(context, {url: html})
        context = landing_audit.run_audit(context, {url: html})
        context = opportunity_engine.run_audit(context, {url: html})
        
        # Ensure no defects were found
        defects = [f for f in context.findings if f.type == "defect"]
        self.assertEqual(len(defects), 0)

if __name__ == '__main__':
    unittest.main()
