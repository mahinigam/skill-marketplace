from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any, Optional

def extract_json_ld(html_content: str) -> List[Dict[str, Any]]:
    """Extracts all JSON-LD blocks from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    json_ld_blocks = []
    
    for script in soup.find_all('script', type='application/ld+json'):
        if script.string:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    json_ld_blocks.extend(data)
                elif isinstance(data, dict):
                    # sometimes there's a @graph
                    if '@graph' in data and isinstance(data['@graph'], list):
                        json_ld_blocks.extend(data['@graph'])
                    else:
                        json_ld_blocks.append(data)
            except json.JSONDecodeError:
                continue
                
    return json_ld_blocks

def extract_canonical_url(html_content: str) -> Optional[str]:
    """Extracts the canonical URL from the head."""
    soup = BeautifulSoup(html_content, 'html.parser')
    link = soup.find('link', rel='canonical')
    if link and link.get('href'):
        return str(link.get('href'))
    return None

def extract_visible_text(html_content: str) -> str:
    """Extracts visible text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style", "noscript", "meta", "link", "head"]):
        script.extract()
    
    text = soup.get_text(separator=' ', strip=True)
    return text

def extract_title(html_content: str) -> Optional[str]:
    """Extracts the page title."""
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('title')
    if title and title.string:
        return title.string.strip()
    return None

def extract_links(html_content: str, base_url: str = "") -> List[str]:
    """Extracts all links from the page."""
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Very basic normalization, we can improve later
        if href.startswith('http'):
            links.append(href)
        elif href.startswith('/') and base_url:
            links.append(base_url.rstrip('/') + href)
    return list(set(links))
