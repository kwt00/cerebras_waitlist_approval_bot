# import os
# import re
# import json
# from typing import List, Dict, Set, Optional
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from dotenv import load_dotenv

# load_dotenv()

# class SheetHandler:
#     def __init__(self):
#         self.service = self._setup_sheets_service()
#         self.EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
#         self.LINKEDIN_PATTERN = r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_/]+"
#         self.TWITTER_PATTERN = r"https?:\/\/(?:www\.)?(?:twitter\.com|x\.com)\/[A-Za-z0-9_]+(?:\/[A-Za-z0-9_]+)?\/?$"
        
#         # Define fixed column structure
#         self.OUTPUT_COLUMNS = [
#             'name',
#             'email',
#             'linkedin',
#             'twitter',
#             'category',
#             'title',
#             'company',
#             'location',
#             'priority',
#             'priority_reasoning',
#             'email_draft',
#             'company_research'
#         ]
        
#         # Get accept-only mode from environment
#         self.accept_only = os.getenv('ACCEPT_ONLY', 'false').lower() == 'true'
#         self.processed_rows = set()

#     def _setup_sheets_service(self):
#         """Initialize the Google Sheets API service."""
#         credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
#         if not credentials_json:
#             raise ValueError("Missing Google Sheets credentials")

#         credentials_info = json.loads(credentials_json)
#         credentials = service_account.Credentials.from_service_account_info(
#             credentials_info,
#             scopes=['https://www.googleapis.com/auth/spreadsheets']
#         )
#         return build('sheets', 'v4', credentials=credentials)

#     def get_input_sheet_width(self, spreadsheet_id: str) -> int:
#         """Get the number of columns in the input sheet."""
#         try:
#             result = self.service.spreadsheets().values().get(
#                 spreadsheetId=spreadsheet_id,
#                 range='input!A1:Z1'
#             ).execute()
#             if 'values' in result and result['values']:
#                 return len(result['values'][0])
#             return 10  # Default fallback
#         except Exception as e:
#             print(f"Error getting input sheet width: {e}")
#             return 10

#     def mark_row_processed(self, spreadsheet_id: str, row_number: int):
#         """Mark a row as processed with highlighting."""
#         if row_number not in self.processed_rows:
#             self._mark_input_row_processed(spreadsheet_id, row_number)
#             self.processed_rows.add(row_number)

#     def _mark_input_row_processed(self, spreadsheet_id: str, row_number: int):
#         """Mark input row as processed with correct width."""
#         try:
#             input_width = self.get_input_sheet_width(spreadsheet_id)
#             sheet_ids = self._get_sheet_ids(spreadsheet_id)
            
#             if sheet_ids.get('input') is not None:
#                 request = {
#                     'repeatCell': {
#                         'range': {
#                             'sheetId': sheet_ids['input'],
#                             'startRowIndex': row_number - 1,
#                             'endRowIndex': row_number,
#                             'startColumnIndex': 0,
#                             'endColumnIndex': input_width
#                         },
#                         'cell': {
#                             'userEnteredFormat': {
#                                 'backgroundColor': {
#                                     'red': 0.95,
#                                     'green': 0.95,
#                                     'blue': 0.86
#                                 }
#                             }
#                         },
#                         'fields': 'userEnteredFormat.backgroundColor'
#                     }
#                 }
                
#                 self.service.spreadsheets().batchUpdate(
#                     spreadsheetId=spreadsheet_id,
#                     body={'requests': [request]}
#                 ).execute()
#                 print(f"Marked input row {row_number} as processed")
#         except Exception as e:
#             print(f"Error marking input row as processed: {e}")

#     def _get_processed_candidates(self, spreadsheet_id: str) -> Set[str]:
#         """Retrieve processed emails, LinkedIn URLs, and Twitter handles."""
#         try:
#             result = self.service.spreadsheets().values().get(
#                 spreadsheetId=spreadsheet_id,
#                 range='output!A2:L'
#             ).execute()

#             processed = set()
#             rows = result.get('values', [])
#             for row in rows:
#                 row_text = ' '.join(row)
#                 processed.update(email.lower() for email in re.findall(self.EMAIL_PATTERN, row_text))
#                 processed.update(url.lower() for url in re.findall(self.LINKEDIN_PATTERN, row_text))
#                 processed.update(url.lower() for url in re.findall(self.TWITTER_PATTERN, row_text))
#             return processed

#         except Exception as e:
#             print(f"Error fetching processed candidates: {e}")
#             return set()

#     def get_candidates(self, spreadsheet_id: str) -> List[Dict]:
#         """Identify unprocessed candidates from the input sheet."""
#         processed = self._get_processed_candidates(spreadsheet_id)
#         try:
#             result = self.service.spreadsheets().values().get(
#                 spreadsheetId=spreadsheet_id,
#                 range='input!A:Z'
#             ).execute()
#         except Exception as e:
#             print(f"Error fetching input data: {e}")
#             return []

#         candidates = []
#         rows = result.get('values', [])[1:]  # Skip header
#         for row_idx, row in enumerate(rows, start=2):
#             try:
#                 row_text = ' '.join(row)
#                 emails = re.findall(self.EMAIL_PATTERN, row_text)
#                 linkedin_urls = re.findall(self.LINKEDIN_PATTERN, row_text)
#                 twitter_urls = re.findall(self.TWITTER_PATTERN, row_text)

#                 email = emails[0].lower() if emails else None
#                 linkedin = linkedin_urls[0] if linkedin_urls else None
#                 twitter = twitter_urls[0] if twitter_urls else None

#                 if (email or linkedin or twitter) and not any(id in processed for id in [email, linkedin, twitter] if id):
#                     candidates.append({
#                         'email': email,
#                         'linkedin': linkedin,
#                         'twitter': twitter,
#                         'row_data': row,
#                         'row_number': row_idx
#                     })
#             except Exception as e:
#                 print(f"Error processing row {row_idx}: {e}")

#         return candidates

#     def save_analysis(self, spreadsheet_id: str, data: Dict, input_row_number: Optional[int] = None):
#         """Save analysis results with improved input sheet handling."""
#         try:
#             # Always mark input row as processed first
#             if input_row_number:
#                 self.mark_row_processed(spreadsheet_id, input_row_number)

#             # Check if we should skip saving to output due to accept-only mode
#             skip_due_to_accept_only = self.accept_only and data.get('priority', '').lower() != 'accept'
#             if skip_due_to_accept_only:
#                 print(f"Skipping non-accepted candidate in accept-only mode (priority: {data.get('priority')})")
#                 return

#             print("\nPreparing row data for sheets:")
#             row = [str(data.get(col, 'MISSING')).replace('\n', '\\n') for col in self.OUTPUT_COLUMNS]

#             result = self.service.spreadsheets().values().append(
#                 spreadsheetId=spreadsheet_id,
#                 range='output!A:L',
#                 valueInputOption='USER_ENTERED',
#                 insertDataOption='INSERT_ROWS',
#                 body={'values': [row]}
#             ).execute()
            
#             updates = result.get('updates', {})
#             updated_range = updates.get('updatedRange', '')
#             output_row_number = int(re.search(r'(\d+)', updated_range).group(1)) if re.search(r'(\d+)', updated_range) else None
            
#             if output_row_number:
#                 priority = data.get('priority', '').lower()
#                 self._apply_output_row_formatting(spreadsheet_id, output_row_number, priority)
#                 print(f"Applied {priority} formatting to output row {output_row_number}")
            
#         except Exception as e:
#             print(f"Error saving analysis: {e}")

#     def _get_sheet_ids(self, spreadsheet_id: str) -> Dict[str, int]:
#         """Get sheet IDs for input and output sheets."""
#         try:
#             spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
#             sheet_ids = {}
#             for sheet in spreadsheet['sheets']:
#                 title = sheet['properties']['title'].lower()
#                 if title in ['input', 'output']:
#                     sheet_ids[title] = sheet['properties']['sheetId']
#             return sheet_ids
#         except Exception as e:
#             print(f"Error getting sheet IDs: {e}")
#             return {'input': 0, 'output': 1}

#     def _apply_output_row_formatting(self, spreadsheet_id: str, row_number: int, priority: str):
#         """Apply formatting only to output row."""
#         try:
#             sheet_ids = self._get_sheet_ids(spreadsheet_id)
#             colors = {
#                 'accept': {'red': 0.8, 'green': 0.9, 'blue': 0.8},     # Light green
#                 'review': {'red': 1.0, 'green': 0.9, 'blue': 0.6},     # Yellow
#                 'reject': {'red': 1.0, 'green': 0.8, 'blue': 0.8}      # Light red
#             }
            
#             if sheet_ids.get('output') is not None:
#                 request = {
#                     'repeatCell': {
#                         'range': {
#                             'sheetId': sheet_ids['output'],
#                             'startRowIndex': row_number - 1,
#                             'endRowIndex': row_number,
#                             'startColumnIndex': 0,
#                             'endColumnIndex': len(self.OUTPUT_COLUMNS)
#                         },
#                         'cell': {
#                             'userEnteredFormat': {
#                                 'backgroundColor': colors.get(priority, {'red': 1.0, 'green': 1.0, 'blue': 1.0})
#                             }
#                         },
#                         'fields': 'userEnteredFormat.backgroundColor'
#                     }
#                 }
                
#                 self.service.spreadsheets().batchUpdate(
#                     spreadsheetId=spreadsheet_id,
#                     body={'requests': [request]}
#                 ).execute()
#         except Exception as e:
#             print(f"Error applying output formatting: {e}")














import os
import re
import json
from typing import List, Dict, Set, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from control_panel import ControlPanel

load_dotenv()

class SheetHandler:
    def __init__(self, control_panel: Optional[ControlPanel] = None):
        self.controls = control_panel or ControlPanel()
        self.service = self._setup_sheets_service()
        self.EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        self.LINKEDIN_PATTERN = r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_/]+"
        self.processed_rows = set()

    def _setup_sheets_service(self):
        """Initialize Google Sheets API service."""
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

    def _clean_cell_value(self, value: str) -> str:
        """Clean whitespace and normalize cell value."""
        if not value:
            return ""
        return ' '.join(str(value).strip().split())

    def _clean_row_data(self, row: list) -> list:
        """Clean all cells in a row."""
        return [self._clean_cell_value(cell) for cell in row]

    def get_candidates(self, spreadsheet_id: str) -> List[Dict]:
        """Get unprocessed candidates from sheet."""
        try:
            processed = self._get_processed_candidates(spreadsheet_id)
            input_sheet = self.controls.config["sheet_controls"]["input_sheet_name"]
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{input_sheet}'!A:Z"
            ).execute()
            
            if 'values' not in result:
                return []
                
            headers = self._clean_row_data(result['values'][0])
            candidates = []

            for row_idx, raw_row in enumerate(result['values'][1:], start=2):
                try:
                    row = self._clean_row_data(raw_row)
                    candidate = {
                        'row_number': row_idx,
                        'row_data': row
                    }
                    
                    # Extract email and LinkedIn from row
                    row_text = ' '.join(row)
                    emails = re.findall(self.EMAIL_PATTERN, row_text)
                    linkedin_urls = re.findall(self.LINKEDIN_PATTERN, row_text)
                    
                    if emails:
                        candidate['email'] = emails[0].lower()
                    if linkedin_urls:
                        candidate['linkedin'] = linkedin_urls[0]
                        
                    # Check if unprocessed
                    if not any(id in processed for id in [
                        candidate.get('email', '').lower(), 
                        candidate.get('linkedin', '').lower()
                    ] if id):
                        candidates.append(candidate)
                        
                except Exception as e:
                    print(f"Error processing row {row_idx}: {e}")
                    continue
                    
            return candidates
            
        except Exception as e:
            print(f"Error getting candidates: {e}")
            return []

    def _get_processed_candidates(self, spreadsheet_id: str) -> Set[str]:
        """Get set of processed emails and LinkedIn URLs."""
        try:
            output_sheet = self.controls.config["sheet_controls"]["output_sheet_name"]
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{output_sheet}'!A:L"
            ).execute()
            
            processed = set()
            if 'values' in result:
                # Skip header row
                for row in result['values'][1:]:
                    clean_row = self._clean_row_data(row)
                    row_text = ' '.join(clean_row)
                    processed.update(email.lower() for email in re.findall(self.EMAIL_PATTERN, row_text))
                    processed.update(url.lower() for url in re.findall(self.LINKEDIN_PATTERN, row_text))
                    
            return processed
            
        except Exception as e:
            print(f"Error getting processed candidates: {e}")
            return set()

    def save_analysis(self, spreadsheet_id: str, data: Dict, input_row_number: Optional[int] = None):
        """Save analysis results to sheet."""
        try:
            # Mark input row if enabled
            if input_row_number and self.controls.should_highlight_rows():
                self.mark_row_processed(spreadsheet_id, input_row_number)

            # Get required fields from control panel
            fields = self.controls.get_required_fields()
            
            # Prepare row data
            row = [self._clean_cell_value(str(data.get(field, ''))) for field in fields]

            # Save to output sheet
            output_sheet = self.controls.config["sheet_controls"]["output_sheet_name"]
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"'{output_sheet}'!A:L",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row]}
            ).execute()

            # Write headers if enabled and this is first row
            if self.controls.config["sheet_controls"].get("write_headers"):
                check = self.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{output_sheet}'!A1:A"
                ).execute()
                
                if 'values' not in check:
                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"'{output_sheet}'!A1",
                        valueInputOption='RAW',
                        body={'values': [fields]}
                    ).execute()

        except Exception as e:
            print(f"Error saving analysis: {e}")

    def mark_row_processed(self, spreadsheet_id: str, row_number: int):
        """Mark input row as processed with highlighting."""
        if row_number in self.processed_rows:
            return
            
        try:
            input_sheet = self.controls.config["sheet_controls"]["input_sheet_name"]
            color = self.controls.get_highlight_color()
            
            # Get sheet width
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{input_sheet}'!A1:Z1"
            ).execute()
            width = len(result.get('values', [[]])[0]) if 'values' in result else 10

            # Apply highlighting
            request = {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row_number - 1,
                        'endRowIndex': row_number,
                        'startColumnIndex': 0,
                        'endColumnIndex': width
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': color
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor'
                }
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [request]}
            ).execute()
            
            self.processed_rows.add(row_number)
            
        except Exception as e:
            print(f"Error marking row as processed: {e}")