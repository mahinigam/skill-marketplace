import urllib.robotparser
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Set
from bs4 import BeautifulSoup
import logging
from .http_client import SafeHTTPClient

logger = logging.getLogger("crawler")

class PageCandidate:
    def __init__(self, url: str):
        self.url = url
        self.inbound_links = 0
        self.sitemap_signal = 0
        self.crawl_depth = 999
        self.navigation_score = 0
        self.commercial_relevance = 0
        
    @property
    def importance_score(self) -> float:
        # Depth penalty (closer to root is better)
        depth_score = max(0, 5 - self.crawl_depth)
        
        return (
            (self.navigation_score * 3.0) +
            (self.inbound_links * 0.5) +
            (self.sitemap_signal * 2.0) +
            depth_score +
            (self.commercial_relevance * 2.0)
        )

class SiteCrawler:
    def __init__(self, client: SafeHTTPClient):
        self.client = client
        self.rp = urllib.robotparser.RobotFileParser()
        self.robots_content = None
        self.sitemap_urls = []

    def fetch_robots_txt(self, base_url: str) -> Optional[str]:
        parsed_url = urlparse(base_url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        
        content, _, err = self.client.get(robots_url)
        if not err and content:
            self.rp.parse(content.splitlines())
            self.robots_content = content
            
            for line in content.splitlines():
                if line.lower().startswith("sitemap:"):
                    self.sitemap_urls.append(line.split(":", 1)[1].strip())
            
            return content
        return None

    def can_fetch(self, url: str) -> bool:
        if not self.robots_content:
            return True
        return self.rp.can_fetch(self.client.user_agent, url)

    def fetch_sitemap(self, url: str) -> List[str]:
        urls = []
        if not self.can_fetch(url):
            return urls
            
        content, _, err = self.client.get(url)
        if not err and content:
            try:
                if "<urlset" in content or "<sitemapindex" in content:
                    root = ET.fromstring(content)
                    for elem in root.iter():
                        if '}' in elem.tag:
                            elem.tag = elem.tag.split('}', 1)[1]
                            
                    if root.tag == "sitemapindex":
                        for loc in root.findall(".//loc"):
                            if loc.text:
                                urls.extend(self.fetch_sitemap(loc.text.strip()))
                    else:
                        for loc in root.findall(".//loc"):
                            if loc.text:
                                urls.append(loc.text.strip())
            except ET.ParseError:
                pass
        return urls

    def _assess_commercial_relevance(self, url: str) -> int:
        keywords = ["product", "item", "pricing", "features", "enterprise", "about", "company", "docs", "category"]
        lower_url = url.lower()
        for kw in keywords:
            if kw in lower_url:
                return 1
        return 0

    def discover_pages(self, start_url: str, max_pages: int = 50) -> List[str]:
        """
        Discovers pages using a PageImportance model.
        """
        self.fetch_robots_txt(start_url)
        candidates: Dict[str, PageCandidate] = {}
        
        def get_or_create(u: str) -> PageCandidate:
            if u not in candidates:
                candidates[u] = PageCandidate(u)
                candidates[u].commercial_relevance = self._assess_commercial_relevance(u)
            return candidates[u]

        # 1. Sitemaps
        for sm in self.sitemap_urls:
            for u in self.fetch_sitemap(sm):
                get_or_create(u).sitemap_signal = 1
                
        if not self.sitemap_urls:
            parsed_url = urlparse(start_url)
            default_sm = f"{parsed_url.scheme}://{parsed_url.netloc}/sitemap.xml"
            for u in self.fetch_sitemap(default_sm):
                get_or_create(u).sitemap_signal = 1

        # 2. Shallow crawl for nav links & inbound tracking
        get_or_create(start_url).crawl_depth = 0
        
        content, _, err = self.client.get(start_url)
        if not err and content:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find nav links
            nav_tags = soup.find_all(['nav', 'header', 'footer'])
            nav_links = set()
            for tag in nav_tags:
                for a in tag.find_all('a', href=True):
                    full = urljoin(start_url, a['href'])
                    if urlparse(full).netloc == urlparse(start_url).netloc:
                        nav_links.add(full)
            
            # All links
            for a in soup.find_all('a', href=True):
                full_url = urljoin(start_url, a['href'])
                if urlparse(full_url).netloc == urlparse(start_url).netloc:
                    if self.can_fetch(full_url):
                        c = get_or_create(full_url)
                        c.inbound_links += 1
                        if c.crawl_depth > 1:
                            c.crawl_depth = 1
                        if full_url in nav_links:
                            c.navigation_score = 1
        
        # Sort by importance and return top
        sorted_candidates = sorted(
            candidates.values(), 
            key=lambda c: c.importance_score, 
            reverse=True
        )
        
        # Prioritize the most important URLs up to max_pages
        return [c.url for c in sorted_candidates[:max_pages]]
