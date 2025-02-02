from typing import Dict, List, Any, Literal
from pydantic import Field
from langchain.tools import BaseTool
import requests
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from crewai_tools import SerperDevTool

class LinkValidator(BaseTool):
    name: Literal["link_validator"] = "link_validator"
    description: Literal["A tool to validate URLs and check their content freshness"] = "A tool to validate URLs and check their content freshness"
    headers: Dict = Field(default_factory=lambda: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    def _run(self, query: Any) -> Dict:
        """Run the URL validation"""
        if isinstance(query, str):
            return self._validate_single_url(query)
        elif isinstance(query, list):
            return self._validate_urls(query)
        else:
            return {"valid": False, "reason": "Invalid input type"}

    async def _arun(self, query: Any) -> Dict:
        """Async execution - falls back to sync for now"""
        return self._run(query)

    def _validate_single_url(self, url: str) -> Dict:
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return {"valid": False, "url": url, "reason": "Malformed URL"}
            
            response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
            
            if response.status_code == 200:
                response = requests.get(url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                date_meta = soup.find('meta', {'property': ['article:published_time', 'og:published_time']})
                if date_meta:
                    pub_date = datetime.fromisoformat(date_meta['content'].split('T')[0])
                    age_in_years = (datetime.now() - pub_date).days / 365
                    if age_in_years > 2:
                        return {"valid": False, "url": url, "reason": "Content too old"}
                
                return {"valid": True, "url": response.url}
            return {"valid": False, "url": url, "reason": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"valid": False, "url": url, "reason": str(e)}

    def _validate_urls(self, urls: List[str]) -> List[Dict]:
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(self._validate_single_url, urls))
        return [result for result in results if result["valid"]]


class EnhancedSerperDevTool(SerperDevTool):
    validator: LinkValidator = Field(default_factory=LinkValidator)
    
    def execute(self, query: str) -> str:
        # Get initial search results
        results = super().execute(query)
        
        # Extract URLs from the results
        import re
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', results)
        
        if not urls:
            return results
            
        # Validate URLs
        valid_results = self.validator._run(urls)
        
        # Replace invalid URLs in the results
        final_results = results
        for url in urls:
            if not any(r["url"] == url for r in valid_results):
                final_results = final_results.replace(url, "")
        
        return final_results

    class Config:
        arbitrary_types_allowed = True