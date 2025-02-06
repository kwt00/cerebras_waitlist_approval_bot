import os
import re
import json
from typing import List, Dict, Set
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

class SheetHandler:
    def __init__(self):
        self.service = self._setup_sheets_service()
        self.EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        self.LINKEDIN_PATTERN = r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_/]+"
        self.TWITTER_PATTERN = r"https?:\/\/(?:www\.)?(?:twitter\.com|x\.com)\/[A-Za-z0-9_]+(?:\/[A-Za-z0-9_]+)?\/?$"

    def _setup_sheets_service(self):
        """Initialize the Google Sheets API service."""
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            raise ValueError("Missing Google Sheets credentials")

        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return build('sheets', 'v4', credentials=credentials)

    def _get_processed_candidates(self, spreadsheet_id: str) -> Set[str]:
        """Retrieve processed emails, LinkedIn URLs, and Twitter handles."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='output!A2:Z'
            ).execute()

            processed = set()
            rows = result.get('values', [])
            for row in rows:
                row_text = ' '.join(row)
                processed.update(email.lower() for email in re.findall(self.EMAIL_PATTERN, row_text))
                processed.update(url.lower() for url in re.findall(self.LINKEDIN_PATTERN, row_text))
                processed.update(url.lower() for url in re.findall(self.TWITTER_PATTERN, row_text))
            return processed

        except Exception as e:
            print(f"Error fetching processed candidates: {e}")
            return set()

    def get_candidates(self, spreadsheet_id: str) -> List[Dict]:
        """Identify unprocessed candidates from the input sheet."""
        processed = self._get_processed_candidates(spreadsheet_id)
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='input!A:Z'
            ).execute()
        except Exception as e:
            print(f"Error fetching input data: {e}")
            return []

        candidates = []
        rows = result.get('values', [])[1:]  # Skip header
        for row_idx, row in enumerate(rows, start=2):
            try:
                row_text = ' '.join(row)
                emails = re.findall(self.EMAIL_PATTERN, row_text)
                linkedin_urls = re.findall(self.LINKEDIN_PATTERN, row_text)
                twitter_urls = re.findall(self.TWITTER_PATTERN, row_text)

                email = emails[0].lower() if emails else None
                linkedin = linkedin_urls[0] if linkedin_urls else None
                twitter = twitter_urls[0] if twitter_urls else None

                if (email or linkedin or twitter) and not any(id in processed for id in [email, linkedin, twitter] if id):
                    candidates.append({
                        'email': email,
                        'linkedin': linkedin,
                        'twitter': twitter,
                        'row_data': row,
                        'row_number': row_idx
                    })
            except Exception as e:
                print(f"Error processing row {row_idx}: {e}")

        return candidates


    def save_analysis(self, spreadsheet_id: str, data: Dict):
        """Save analysis results to the output sheet."""
        try:
            print("\nPreparing row data for sheets:")
            # Prepare row data
            row = [
                data.get('name', 'MISSING'),
                data.get('email', 'MISSING'), 
                data.get('linkedin', 'MISSING'), 
                data.get('twitter', 'MISSING'),
                data.get('category', 'MISSING'),
                data.get('title', 'MISSING'),
                data.get('company', 'MISSING'),
                data.get('location', 'MISSING'),
                data.get('priority', 'MISSING'),
                data.get('priority_reasoning', 'MISSING').replace('\n', '\\n'),
                data.get('email_draft', 'MISSING').replace('\n', '\\n')
            ]

            print("Row data prepared:")
            print(f"Email field: {row[1]}")
            print(f"LinkedIn field: {row[2]}")

            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='output!A:K',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': [row]}
            ).execute()
            
            updates = result.get('updates', {})
            updated_range = updates.get('updatedRange', '')
            # Extract row number from range (e.g., 'Sheet1!A5:K5' -> 5)
            row_number = int(re.search(r'(\d+)', updated_range).group(1)) if re.search(r'(\d+)', updated_range) else None
            
            if row_number:
                priority = data.get('priority', '').lower()
                self._apply_row_formatting(spreadsheet_id, row_number, priority)
                print(f"Applied {priority} formatting to row {row_number}")
            
        except Exception as e:
            print(f"Error saving analysis: {e}")

    def _get_sheet_ids(self, spreadsheet_id: str) -> Dict[str, int]:
        """Get sheet IDs for input and output sheets."""
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_ids = {}
            for sheet in spreadsheet['sheets']:
                title = sheet['properties']['title'].lower()
                if title in ['input', 'output']:
                    sheet_ids[title] = sheet['properties']['sheetId']
            return sheet_ids
        except Exception as e:
            print(f"Error getting sheet IDs: {e}")
            return {'input': 0, 'output': 1}  # Default fallback

    def _apply_row_formatting(self, spreadsheet_id: str, row_number: int, priority: str):
        """Apply color formatting based on priority."""
        try:
            sheet_ids = self._get_sheet_ids(spreadsheet_id)
            colors = {
                'accept': {'red': 0.8, 'green': 0.9, 'blue': 0.8},     # Light green
                'review': {'red': 1.0, 'green': 0.9, 'blue': 0.6},     # Yellow
                'reject': {'red': 1.0, 'green': 0.8, 'blue': 0.8},     # Light red
                'processed': {'red': 0.95, 'green': 0.95, 'blue': 0.86}  # Beige
            }
            
            requests = []
            
            if sheet_ids.get('output') is not None:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_ids['output'],
                            'startRowIndex': row_number - 1,
                            'endRowIndex': row_number,
                            'startColumnIndex': 0,
                            'endColumnIndex': 11
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': colors.get(priority, {'red': 1.0, 'green': 1.0, 'blue': 1.0})
                            }
                        },
                        'fields': 'userEnteredFormat.backgroundColor'
                    }
                })

            if sheet_ids.get('input') is not None:
                # Note: row_number - 1 because we want to mark the original input row
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_ids['input'],
                            'startRowIndex': row_number - 1,
                            'endRowIndex': row_number,
                            'startColumnIndex': 0,
                            'endColumnIndex': 11
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': colors['processed']
                            }
                        },
                        'fields': 'userEnteredFormat.backgroundColor'
                    }
                })
            
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
        except Exception as e:
            print(f"Error applying formatting: {e}")