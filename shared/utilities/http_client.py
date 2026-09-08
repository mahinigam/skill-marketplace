import httpx
from urllib.parse import urlparse
import time
from typing import Optional, Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("http_client")

class SafeHTTPClient:
    def __init__(self, user_agent: str = "AgentSkillMarketplace/1.0", timeout_sec: int = 10):
        self.user_agent = user_agent
        self.timeout = timeout_sec
        self.client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True
        )
        self.last_request_time: Dict[str, float] = {}
        self.rate_limit_delay = 1.0 # 1 second between requests to the same domain

    def _respect_rate_limit(self, domain: str):
        now = time.time()
        if domain in self.last_request_time:
            elapsed = now - self.last_request_time[domain]
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time[domain] = time.time()

    def get(self, url: str) -> Tuple[Optional[str], Optional[httpx.Response], Optional[str]]:
        """
        Returns (content, response_object, error_message)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            self._respect_rate_limit(domain)

            logger.info(f"Fetching {url}")
            response = self.client.get(url)
            
            # Raise for status but capture it if needed
            response.raise_for_status()
            
            # limit size to 5MB to prevent huge page bombing
            if len(response.content) > 5 * 1024 * 1024:
                return None, response, f"Content too large: {len(response.content)} bytes"
                
            return response.text, response, None

        except httpx.HTTPStatusError as e:
            return None, e.response, f"HTTP Error: {e.response.status_code}"
        except httpx.RequestError as e:
            return None, None, f"Request Error: {str(e)}"
        except Exception as e:
            return None, None, f"Unexpected Error: {str(e)}"

    def close(self):
        self.client.close()

# Singleton instance for simple use cases
default_client = SafeHTTPClient()
