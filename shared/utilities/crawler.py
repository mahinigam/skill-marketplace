import urllib.robotparser
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET
from typing import List, Optional
from bs4 import BeautifulSoup
import logging
from .http_client import SafeHTTPClient

logger = logging.getLogger("crawler")

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
            
            # Extract sitemaps
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
            logger.info(f"Blocked by robots.txt: {url}")
            return urls
            
        content, _, err = self.client.get(url)
        if not err and content:
            try:
                # Handle standard sitemap XML
                if "<urlset" in content or "<sitemapindex" in content:
                    root = ET.fromstring(content)
                    # Namespaces can be tricky, strip them for simple finding
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
                logger.warning(f"Failed to parse sitemap: {url}")
        return urls

    def discover_pages(self, start_url: str, max_pages: int = 50) -> List[str]:
        """
        Discovers pages starting from start_url. First checks sitemap, 
        then falls back to basic breadth-first crawling if needed.
        Returns a sampled list of URLs.
        """
        self.fetch_robots_txt(start_url)
        discovered = set()
        
        # 1. Try sitemaps from robots.txt
        for sm in self.sitemap_urls:
            discovered.update(self.fetch_sitemap(sm))
            
        # 2. Try default sitemap location if none found
        if not self.sitemap_urls:
            parsed_url = urlparse(start_url)
            default_sm = f"{parsed_url.scheme}://{parsed_url.netloc}/sitemap.xml"
            discovered.update(self.fetch_sitemap(default_sm))
            
        # 3. Always include start URL
        discovered.add(start_url)
        
        # 4. If we have very few pages, do a shallow crawl from start_url
        if len(discovered) < 5:
            content, _, err = self.client.get(start_url)
            if not err and content:
                soup = BeautifulSoup(content, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_url = urljoin(start_url, href)
                    # Stay on domain
                    if urlparse(full_url).netloc == urlparse(start_url).netloc:
                        if self.can_fetch(full_url):
                            discovered.add(full_url)
                            if len(discovered) >= max_pages:
                                break
                                
        # Sample pages (prioritize shorter URLs as they are often more important/category pages)
        sorted_urls = sorted(list(discovered), key=len)
        return sorted_urls[:max_pages]
