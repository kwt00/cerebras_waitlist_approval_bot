import os
import re
import json
import time
from typing import Dict, Optional, List
from enum import Enum
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from exa_py import Exa
from cerebras.cloud.sdk import Cerebras

load_dotenv()

class CustomerCategory(Enum):
    STUDENT = "student"
    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    OTHER = "other"

class LinkedInScraper:
    def __init__(self):
        self.exa = Exa(api_key=os.getenv('EXA_KEY'))
        self.sheets_service = self._setup_google_sheets()
        
    def _setup_google_sheets(self):
        try:
            credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if not credentials_json:
                raise ValueError("Missing Google Sheets credentials")
            
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            return build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            print(f"Failed to setup Google Sheets: {e}")
            raise

    def _highlight_row(self, spreadsheet_id: str, row_index: int):
        try:
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row_index - 1,
                        'endRowIndex': row_index,
                        'startColumnIndex': 0,
                        'endColumnIndex': 999
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 1.0,
                                'green': 0.9,
                                'blue': 0.9
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor'
                }
            }]
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            print(f"Row {row_index} highlighted for manual verification")
        except Exception as e:
            print(f"Failed to highlight row {row_index}: {e}")

    def _extract_domain_from_email(self, email: str) -> Optional[str]:
        """Extract domain from email address using specified regex."""
        if not email:
            return None
        domain_match = re.search(r'(?<=@)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email)
        return domain_match.group(0) if domain_match else None

    def _get_domain_info(self, domain: str) -> Optional[str]:
        """Research domain using Exa search."""
        try:
            search_query = f'"{domain}" company OR organization OR institution site:.com OR site:.edu OR site:.org -site:{domain}'
            results = self.exa.search(
                search_query,
                num_results=5,
                include_domains=[".com", ".edu", ".org"],
                exclude_domains=[domain]
            )
            
            if results:
                return "\n".join([f"Title: {r.title}\nSnippet: {r.snippet}" for r in results])
            return None
        except Exception as e:
            print(f"Exa domain search error: {str(e)}")
            return None

    def _determine_category(self, email_domain: str, domain_info: str, analysis_data: dict) -> dict:
        """Research and determine category based on all available information."""
        try:
            prompt = f"""As a Cerebras AI hackathon organizer, evaluate this potential participant based on their information:

Domain Information:
{domain_info if domain_info else "No domain information available"}

LinkedIn Analysis:
{json.dumps(analysis_data, indent=2)}

Evaluate:
1. Organization type (university, startup, enterprise, research lab, etc.)
2. Technical relevance to AI/ML and hardware
3. Potential value from Cerebras technology

Determine:
1. Category: "student", "startup", "enterprise", or "other"
2. Whether to accept them for the hackathon:
   - "accept" for strong technical fit
   - "waitlist" for potential fit but needs more info
   - "reject" for clear mismatch

Format response as JSON with keys: category, decision, reasoning"""

            client = Cerebras(api_key=os.environ.get("CEREBRAS_KEY"))
            response = client.chat.completions.create(
                messages=[{
                    "role": "system",
                    "content": "You are a technical evaluator for Cerebras, analyzing potential hackathon participants."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                model="llama3.3-70b",
                response_format={"type": "json_object"},
                temperature=0.7
            )

            if response and hasattr(response, 'choices'):
                result = json.loads(response.choices[0].message.content)
                return {
                    'category': getattr(CustomerCategory, result['category'].upper(), CustomerCategory.OTHER),
                    'decision': result['decision'],
                    'reasoning': result['reasoning']
                }
            
            return {
                'category': CustomerCategory.OTHER,
                'decision': 'waitlist',
                'reasoning': 'Failed to analyze profile'
            }
            
        except Exception as e:
            print(f"Category determination failed: {e}")
            return {
                'category': CustomerCategory.OTHER,
                'decision': 'waitlist',
                'reasoning': f'Error in analysis: {str(e)}'
            }

    def _load_email_templates(self) -> Dict[str, Dict[str, str]]:
        """Load email templates from predefined structure."""
        return {
            'accept': {
                CustomerCategory.STUDENT.value: """
Hi {name},

{custom_line}

Based on your background in {field_of_study}, we believe you'd be a great fit for our upcoming AI hackathon! You'll get to:

- Work hands-on with Cerebras AI hardware
- Build projects using our Inference API
- Connect with AI researchers and engineers

Join our Discord at cerebras.ai/discord to start collaborating.

Next steps:
1. Complete registration: [LINK]
2. Join Discord: cerebras.ai/discord
3. Review API docs: [DOCS_LINK]

Best,
The Cerebras Team""",
                CustomerCategory.STARTUP.value: """
Hi {name},

{custom_line}

Your startup background and technical expertise make you an ideal participant for our upcoming AI hackathon. You'll have the opportunity to:

- Build on enterprise-grade AI infrastructure
- Network with potential partners
- Create scalable AI solutions

Join our Discord at cerebras.ai/discord to connect with other founders.

Next steps:
1. Register your team: [LINK]
2. Join Discord: cerebras.ai/discord
3. Book intro call: [CALENDAR]

Best regards,
The Cerebras Team""",
                CustomerCategory.ENTERPRISE.value: """
Hi {name},

{custom_line}

Your experience at {company} aligns perfectly with our mission. Our hackathon offers a unique opportunity to:

- Evaluate Cerebras AI infrastructure
- Connect with our technical team
- Prototype enterprise solutions

Join our Discord at cerebras.ai/discord for technical discussions.

Next steps:
1. Register your team: [LINK]
2. Join Discord: cerebras.ai/discord
3. Schedule architecture review: [CALENDAR]

Best regards,
The Cerebras Team"""
            },
            'waitlist': {
                'default': """
Hi {name},

{custom_line}

Thank you for your interest in the Cerebras AI Hackathon. We're currently reviewing applications and will follow up with more details soon.

In the meantime:
- Join our Discord: cerebras.ai/discord
- Explore our API docs: [DOCS_LINK]
- Check out our blog: [BLOG_LINK]

Best regards,
The Cerebras Team"""
            },
            'reject': {
                'default': """
Hi {name},

Thank you for your interest in the Cerebras AI Hackathon. While we appreciate your enthusiasm, we've decided to prioritize participants with more direct AI/ML experience for this event.

We encourage you to:
- Join our Discord community: cerebras.ai/discord
- Follow our blog for future opportunities
- Sign up for our newsletter

Best regards,
The Cerebras Team"""
            }
        }

    def _get_email_template(self, category: CustomerCategory, profile_data: dict, decision: str) -> str:
        """Get appropriate email template based on category and decision."""
        templates = self._load_email_templates()
        
        # Get category-specific template if available, otherwise use default
        if decision in templates:
            category_templates = templates[decision]
            template = category_templates.get(
                category.value,
                category_templates.get('default', templates['waitlist']['default'])
            )
        else:
            template = templates['waitlist']['default']
        
        return template

    def _get_linkedin_data(self, linkedin_url: str):
        try:
            if 'www.linkedin.com' not in linkedin_url:
                linkedin_url = linkedin_url.replace('linkedin.com', 'www.linkedin.com')
            if not linkedin_url.startswith('http'):
                linkedin_url = 'https://' + linkedin_url
            if not linkedin_url.endswith('/'):
                linkedin_url += '/'
                
            print(f"\nFetching: {linkedin_url}")
            
            result = self.exa.get_contents(
                [linkedin_url],
                text=True
            )
            
            if result:
                print("Exa fetch successful!")
                return result
            
            print("No content returned from Exa")
            return None
            
        except Exception as e:
            print(f"Exa error: {str(e)}")
            return None

    def _analyze_with_llm(self, profile_data):
        try:
            prompt = f"""As a Cerebras AI hackathon organizer, analyze this LinkedIn profile:

{profile_data}

Provide a detailed evaluation focusing on their potential to use Cerebras AI hardware and APIs.
Consider:
- Experience with AI/ML
- Hardware expertise
- Systems architecture knowledge
- Software development background
- Open source contributions

Required fields:
1. Full name
2. Current role/title
3. Company
4. Location
5. Category (Engineer, Designer, Product, Business, or Other)
6. Priority for Cerebras hackathon:
   - 'accept' for strong ML/AI/hardware engineering potential
   - 'waitlist' for technical background but unclear AI experience
   - 'reject' for non-technical or unrelated background
7. Detailed reasoning for the decision
8. Personalized email that:
   - References their specific background
   - Invites them to join Cerebras Discord (cerebras.ai/discord)
   - Encourages using Cerebras Inference API
   - Mentions the hackathon opportunity
   - Includes clear next steps
   - Is ready to send (professional, error-free)

Format as JSON with keys: name, title, company, location, category, priority, priority_reasoning, email_draft"""

            messages = [
                {
                    "role": "system",
                    "content": "You are a technical recruiter for Cerebras, evaluating candidates for an AI hackathon. Focus on AI/ML experience and potential to use Cerebras hardware/APIs."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            client = Cerebras(api_key=os.environ.get("CEREBRAS_KEY"))
            response = client.chat.completions.create(
                messages=messages,
                model="llama3.3-70b",
                response_format={"type": "json_object"},
                temperature=0.7
            )

            if response and hasattr(response, 'choices'):
                return json.loads(response.choices[0].message.content)
            return None

        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return None

    def _write_to_output(self, spreadsheet_id: str, data: dict):
        try:
            row = [
                data.get('name', ''),
                data.get('email', ''),
                data.get('linkedin_url', ''),
                data.get('twitter', ''),
                data.get('category', ''),
                data.get('title', ''),
                data.get('company', ''),
                data.get('location', ''),
                data.get('priority', ''),
                data.get('priority_reasoning', ''),
                data.get('email_draft', ''),
                data.get('email_template', '')  # Added new column for template type
            ]

            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='output!A:L',  # Updated to include new column
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row]}
            ).execute()
            
            print("Data written to output sheet")
            return True
        except Exception as e:
            print(f"Error writing to sheet: {e}")
            return False

    def process_sheet(self, spreadsheet_id: str):
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='input!A:Z'
            ).execute()
            
            rows = result.get('values', [])
            if not rows:
                print('No data found in input sheet')
                return

            headers = rows[0]
            linkedin_idx = next((i for i, h in enumerate(headers) if 'linkedin' in str(h).lower()), None)
            email_idx = next((i for i, h in enumerate(headers) 
                            if any(term in str(h).lower() for term in ['email', 'e-mail', 'mail'])), None)

            if linkedin_idx is None:
                print("No LinkedIn column found")
                return

            for row_idx, row in enumerate(rows[1:], start=2):
                if linkedin_idx >= len(row):
                    continue

                linkedin_url = row[linkedin_idx].strip()
                email = row[email_idx].strip() if email_idx and email_idx < len(row) else ''
                
                if not linkedin_url and not email:
                    continue

                print(f"\nProcessing Row {row_idx}")
                
                # Get profile data from LinkedIn or use email domain as fallback
                profile_data = self._get_linkedin_data(linkedin_url) if linkedin_url else None
                
                if not profile_data and email:
                    domain = self._extract_domain_from_email(email)
                    if domain:
                        print(f"Using email domain as fallback: {domain}")
                        # Create minimal profile data from email domain
                        profile_data = f"Email domain: {domain}"

                if not profile_data:
                    print(f"No profile data found for row {row_idx}")
                    self._highlight_row(spreadsheet_id, row_idx)
                    time.sleep(0.5)
                    continue

                # Analyze profile with LLM
                analysis = self._analyze_with_llm(profile_data)
                if not analysis:
                    print(f"LLM analysis failed for row {row_idx}")
                    self._highlight_row(spreadsheet_id, row_idx)
                    time.sleep(0.5)
                    continue

                # Research domain and determine category
                domain = self._extract_domain_from_email(email) if email else None
                domain_info = self._get_domain_info(domain) if domain else None
                
                category_analysis = self._determine_category(
                    domain or '',
                    domain_info or '',
                    analysis
                )
                
                # Generate appropriate email based on category and decision
                email_template = self._get_email_template(
                    category_analysis['category'],
                    analysis,
                    category_analysis['decision']
                )
                
                custom_line = analysis.get('email_draft', '').split('\n')[0]  # Use first line of LLM email as custom
                email_content = email_template.format(
                    name=analysis.get('name'),
                    company=analysis.get('company'),
                    field_of_study=analysis.get('field_of_study', 'AI/ML'),
                    custom_line=custom_line
                )
                
                # Update analysis with category information
                analysis['category'] = category_analysis['category'].value
                analysis['decision'] = category_analysis['decision']
                analysis['decision_reasoning'] = category_analysis['reasoning']
                
                # Update analysis with email content and metadata
                analysis['email'] = email
                analysis['linkedin_url'] = linkedin_url
                analysis['email_draft'] = email_content
                analysis['email_template'] = category.value
                
                self._write_to_output(spreadsheet_id, analysis)
                
                time.sleep(2)

        except Exception as e:
            print(f"Error processing sheet: {e}")

def main():
    try:
        scraper = LinkedInScraper()
        sheet_id = os.getenv('SHEET_ID')
        if not sheet_id:
            raise ValueError("Missing SHEET_ID in environment variables")
        
        print("Starting LinkedIn profile processing...")
        scraper.process_sheet(sheet_id)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()