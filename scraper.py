from typing import Dict, Optional, TypedDict
import re
import os
from exa_py import Exa
from dotenv import load_dotenv

load_dotenv()

class ScrapedData(TypedDict, total=False):
    """Container for scraped data"""
    linkedin_data: Optional[str]
    domain_data: Optional[str]
    errors: list[str]

class DataScraper:
    def __init__(self):
        try:
            self.exa = Exa(api_key=os.getenv('EXA_KEY'))
        except Exception as e:
            print(f"Warning: Failed to initialize Exa: {e}")
            self.exa = None

    def domain_lookup(self, query: str) -> tuple[Optional[str], Optional[str]]:
        """Safely perform an Exa search with error handling"""
        if not self.exa:
            return None, "Exa client not initialized"
            
        try:
            response = self.exa.search_and_contents(
                query,
                type="keyword",
                category="company",
                livecrawl="always",
                text=True,
                summary={
                    "query": "Answer the following questions with no more words than necessary. What field does this company work in? What problem does it solve specifically? How big is the company? Answer format: Field: ... Problem Solved: ... Size: ... "
                },
                num_results=3
            )
            
            if not response or not response.results:
                return None, None
                
            summaries = []
            for result in response.results:
                if result.summary:
                    summaries.append(result.summary + "\n\n\n")
            
            return summaries, None
            
        except Exception as e:
            return None, f"Search error: {str(e)}"

    def linkedin_lookup(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """Safely get contents with error handling"""
        if not self.exa:
            return None, "Exa client not initialized"
            
        try:
            content = self.exa.get_contents([url], text=True)
            return content, None
        except Exception as e:
            return None, f"Content fetch error: {str(e)}"

    def scrape(self, linkedin_url: Optional[str] = None, email: Optional[str] = None) -> ScrapedData:
        """Scrape data from all available sources"""
        result: ScrapedData = {"errors": []}

        if linkedin_url:
            try:
                content, error = self.linkedin_lookup(linkedin_url)
                if content:
                    result["linkedin_data"] = content
                if error:
                    result["errors"].append(f"LinkedIn: {error}")
            except Exception as e:
                result["errors"].append(f"LinkedIn processing failed: {str(e)}")

        if email:
            try:
                domain_match = re.search(r'@([\w.-]+)', email)
                if domain_match:
                    domain = domain_match.group(1)
                    domain_content, error = self.domain_lookup(domain)
                    if domain_content:
                        result["domain_data"] = domain_content
                    if error:
                        result["errors"].append(f"Domain search: {error}")
            except Exception as e:
                result["errors"].append(f"Domain processing failed: {str(e)}")

        return result