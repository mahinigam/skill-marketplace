import sys
import os
import unittest
import json
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.models.models import AuditContext, AuditTarget, CrawlRecord, FindingType
from shared.utilities.crawler import SiteCrawler
from shared.utilities.scoring import fuse_findings, correlate_root_causes, calculate_readiness_score
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
        url = "https://site01.com"
        responses = {
            f"{url}/robots.txt": "User-agent: *\nDisallow: /products/\nSitemap: https://site01.com/sitemap.xml\n",
            f"{url}/sitemap.xml": "<urlset><loc>https://site01.com/products/1</loc></urlset>"
        }
        client = MockHTTPClient(responses)
        crawler = SiteCrawler(client)
        crawler.fetch_robots_txt(url)
        context = self.base_context(url)
        
        context = crawl_audit.run_audit(context, crawler)
        self.assertTrue(len(crawler.sitemap_urls) > 0)
        self.assertFalse(crawler.can_fetch(f"{url}/products/1"))

    def test_site_02_js_only_content(self):
        url = "https://site02.com/product/1"
        payload = 'lots of hidden text ' * 1000
        html = f'<html><body><script>{{"huge_json_payload": "{payload}"}}</script></body></html>'
        
        context = self.base_context(url)
        context = render_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("RENDER-001", findings)

    def test_site_03_missing_structured_data_and_ambiguous(self):
        url = "https://site03.com/product/1"
        html = """<html><body><div>Awesome Product</div><div>Buy now</div></body></html>"""
        
        context = self.base_context(url)
        context = semantic_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("SEM-002", findings)

    def test_site_05_entity_ambiguity(self):
        url = "https://site05.com/about"
        html = """
        <html>
        <head><title>A | B | C - D</title></head>
        <body>
        <script type="application/ld+json">
        [
            {"@type": "Organization", "name": "Apple"},
            {"@type": "Organization", "name": "Apple Inc."}
        ]
        </script>
        </body></html>
        """
        context = self.base_context(url)
        context = entity_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("ENT-001", findings)

    def test_site_06_corroboration_failure(self):
        url = "https://site06.com/product"
        html = """
        <html><body>
        <script type="application/ld+json">
        [
          {"@type": "Product", "sku": "123", "offers": {"price": "10.00"}}
        ]
        </script>
        </body></html>
        """
        html2 = """
        <html><body>
        <script type="application/ld+json">
        [
          {"@type": "Product", "sku": "123", "offers": {"price": "15.00"}}
        ]
        </script>
        </body></html>
        """
        context = self.base_context(url)
        context = freshness_audit.run_audit(context, {url: html, f"{url}/v2": html2})
        
        findings = [f.id for f in context.findings]
        self.assertIn("CORR-001", findings)
        
    def test_site_06_corroboration_healthy_external(self):
        url = "https://site06-healthy.com/product"
        html = """
        <html><body>
        <script type="application/ld+json">
        [
          {"@type": "Product", "sku": "123", "offers": {"price": "10.00"}, "dateModified": "2023-10-10"}
        ]
        </script>
        </body></html>
        """
        context = self.base_context(url)
        context = freshness_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertNotIn("CORR-002", findings)  # Should not fail external corroboration
        
    def test_site_07_answerability(self):
        url = "https://site07.com/product/xyz"
        html = """<html><body><h1>Cool Product</h1><p>Buy this amazing product</p><button>Add to cart</button></body></html>"""
        context = self.base_context(url)
        context = answerability_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("ANS-001", findings)

    def test_site_09_semantic_integrity(self):
        url = "https://site09.com/product/category"
        html = """
        <html><body>
        <div><div class="product">P1</div><div class="product">P2</div></div>
        <p>Price: $10.00</p>
        <p>Price: $20.00</p>
        <p>Price: $30.00</p>
        <p>Price: $40.00</p>
        </body></html>
        """
        context = self.base_context(url)
        context = integrity_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("SEM-001", findings)  # Updated ID based on new logic
        
    def test_site_09_semantic_integrity_healthy(self):
        url = "https://site09-healthy.com/product/1"
        html = """
        <html><body>
        <main>
            <h1>Awesome Widget</h1>
            <p>Price: $50.00</p>
        </main>
        <aside>
            <h2>Cart Total</h2>
            <p>Subtotal: $50.00</p>
            <p>Tax: $5.00</p>
            <p>Total: $55.00</p>
        </aside>
        </body></html>
        """
        context = self.base_context(url)
        # Using integrity_audit because that's how it's named in the import above, though ID is SEM-001
        context = integrity_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertNotIn("SEM-001", findings)
        
    def test_site_10_landing_intent(self):
        url = "https://site10.com/landing"
        html = """
        <html>
        <head><title>Great Answers</title></head>
        <body>
        <div class="modal overlay">Please Login</div>
        </body>
        </html>
        """
        context = self.base_context(url)
        context = landing_audit.run_audit(context, {url: html})
        
        findings = [f.id for f in context.findings]
        self.assertIn("LAND-001", findings)

    def test_scoring_fusion_and_root_cause(self):
        # Create dummy findings to test fusion and root causes
        context = self.base_context("https://test.com")
        html = """
        <html><body>
        <script type="application/ld+json">
        [
            {"@type": "Organization", "name": "A"},
            {"@type": "Organization", "name": "B"}
        ]
        </script>
        </body></html>
        """
        
        context = entity_audit.run_audit(context, {"url1": html})
        context = semantic_audit.run_audit(context, {"url1": "<html><div>ambiguous</div></html>", "url2": "<html><div>ambiguous 2</div></html>"})
        
        # Test Fusion
        fused = fuse_findings(context.findings)
        
        # Test Root Causes
        fused, root_causes = correlate_root_causes(fused)
        
        # Test Scoring
        score = calculate_readiness_score(fused)
        
        self.assertTrue(len(fused) > 0)
        self.assertIsNotNone(score)

if __name__ == '__main__':
    unittest.main()
