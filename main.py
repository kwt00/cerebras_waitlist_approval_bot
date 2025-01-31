import os
import re
import json
import time
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from exa_py import Exa
from cerebras.cloud.sdk import Cerebras

load_dotenv()

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
                data.get('email_draft', '')
            ]

            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='output!A:K',
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
            email_idx = next((i for i, h in enumerate(headers) if 'email' in str(h).lower()), None)

            if linkedin_idx is None:
                print("No LinkedIn column found")
                return

            for row_idx, row in enumerate(rows[1:], start=2):
                if linkedin_idx >= len(row):
                    continue

                linkedin_url = row[linkedin_idx].strip()
                if not linkedin_url:
                    continue

                print(f"\nProcessing Row {row_idx}")
                
                profile_data = self._get_linkedin_data(linkedin_url)
                
                if not profile_data:
                    print(f"No profile data found for row {row_idx}")
                    self._highlight_row(spreadsheet_id, row_idx)
                    time.sleep(0.5) 
                    continue

                analysis = self._analyze_with_llm(profile_data)
                if not analysis:
                    print(f"LLM analysis failed for row {row_idx}")
                    self._highlight_row(spreadsheet_id, row_idx)
                    time.sleep(0.5)
                    continue

                analysis['email'] = row[email_idx] if email_idx and email_idx < len(row) else ''
                analysis['linkedin_url'] = linkedin_url

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