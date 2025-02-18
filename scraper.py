from typing import Dict, Optional, TypedDict
import re
import os
from exa_py import Exa
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()

class ScrapedData(TypedDict, total=False):
    """Container for scraped data"""
    linkedin_data: Optional[str]
    company_research: Optional[str]
    errors: list[str]

class DataScraper:
    def __init__(self):
        try:
            self.exa = Exa(api_key=os.getenv('EXA_KEY'))
            self.cerebras = Cerebras(api_key=os.getenv("CEREBRAS_KEY"))
        except Exception as e:
            print(f"Warning: Failed to initialize APIs: {e}")
            self.exa = None
            self.cerebras = None
            
        self.common_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 
            'outlook.com', 'aol.com', 'icloud.com'
        }

    def _extract_company_from_linkedin(self, profile_data: str) -> Optional[str]:
        """Extract company name from LinkedIn profile data."""
        try:
            prompt = """Extract the current company name from this LinkedIn profile text. 
            If multiple companies are listed, return only the most recent/current one.
            Return ONLY the company name, nothing else."""
            
            response = self.cerebras.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You extract company names from text. Return only the company name."},
                    {"role": "user", "content": f"{prompt}\n\nProfile:\n{profile_data}"}
                ],
                model="llama3.3-70b",
                temperature=0
            )
            
            company = response.choices[0].message.content.strip()
            return company if company and company.lower() != "none" else None
            
        except Exception as e:
            print(f"Error extracting company from LinkedIn: {e}")
            return None

    def _research_company(self, company_name: str) -> Optional[str]:
        """Research company using Exa search."""
        if not self.exa or not company_name:
            return None
            
        try:
            print(f"Researching company: {company_name}")
            search_query = f'"{company_name}" startup company AI "machine learning"'
            results = self.exa.search_and_contents(
                search_query,
                num_results=3,
                text=True
            )
            
            if not results or not results.results:
                return None
                
            summaries = []
            for result in results.results:
                if result.text:
                    summaries.append(f"Source: {result.title}\n{result.text[:500]}...")
            
            return "\n\n".join(summaries) if summaries else None
            
        except Exception as e:
            print(f"Company research error: {str(e)}")
            return None

    def _extract_domain_from_email(self, email: str) -> Optional[str]:
        """Extract domain from email address."""
        if not email:
            return None
        try:
            return email.split('@')[1].lower()
        except:
            return None

    def scrape(self, linkedin_url: Optional[str] = None, email: Optional[str] = None) -> ScrapedData:
        """Enhanced scrape with company research."""
        result: ScrapedData = {"errors": []}
        company_name = None

        # First try to get company from LinkedIn
        if linkedin_url:
            try:
                print("Getting LinkedIn data...")
                profile_content = self.exa.get_contents([linkedin_url], text=True)
                if profile_content:
                    result["linkedin_data"] = profile_content
                    company_name = self._extract_company_from_linkedin(profile_content)
                    if company_name:
                        print(f"Found company from LinkedIn: {company_name}")
            except Exception as e:
                result["errors"].append(f"LinkedIn processing failed: {str(e)}")

        # If no company from LinkedIn, try email domain
        if not company_name and email:
            domain = self._extract_domain_from_email(email)
            if domain and domain not in self.common_domains:
                company_name = domain
                print(f"Using email domain as company: {domain}")

        # Do company research if we found a company name
        if company_name:
            research = self._research_company(company_name)
            if research:
                result["company_research"] = research
                print("✓ Added company research")
            else:
                result["errors"].append(f"No research found for company: {company_name}")

        return result