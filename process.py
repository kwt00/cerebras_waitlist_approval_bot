# import os
# import time
# from typing import Dict, Optional
# from dotenv import load_dotenv
# from scraper import DataScraper
# from sheet_handler import SheetHandler
# from inference import Inference

# load_dotenv()

# class CandidateProcessor:
#     def __init__(self):
#         """Initialize processor with required components."""
#         self.scraper = DataScraper()
#         self.sheets = SheetHandler()
#         self.inference = Inference()
#         self.sheet_id = os.getenv('SHEET_ID')
        
#         if not self.sheet_id:
#             raise ValueError("SHEET_ID environment variable is required")

#     def process_candidate(self, candidate_data: Dict) -> bool:
#         """Process a single candidate.
        
#         Args:
#             candidate_data: Dictionary containing candidate information
            
#         Returns:
#             bool: True if processing was successful
#         """
#         try:
#             email = candidate_data.get('email', '').strip()
#             linkedin = candidate_data.get('linkedin', '').strip()
#             row_number = candidate_data.get('row_number')
            
#             print(f"\nProcessing candidate from row {row_number}")
#             print(f"LinkedIn: {linkedin or 'None'}")
#             print(f"Email: {email or 'None'}")
            
#             if not linkedin and not email:
#                 print("No LinkedIn or email - marking row as processed")
#                 if row_number:
#                     self.sheets.mark_row_processed(self.sheet_id, row_number)
#                 return False

#             # Step 1: Scrape data
#             print("\nScraping data...")
#             scrape_result = self.scraper.scrape(
#                 linkedin_url=linkedin,
#                 email=email
#             )
            
#             if not scrape_result.get('linkedin_data') and not scrape_result.get('company_research'):
#                 print("No data found from scraping")
            
#             # Step 2: Run analysis
#             print("\nAnalyzing candidate...")
#             analysis = self.inference.analyze_candidate(
#                 profile_data=scrape_result.get('linkedin_data'),
#                 company_data=scrape_result.get('company_research'),
#                 email=email,
#                 linkedin_url=linkedin
#             )

#             # Add the scraped data and any available fields from input
#             analysis.update({
#                 'email': email,
#                 'linkedin': linkedin,
#                 'company_research': scrape_result.get('company_research', ''),
#                 'name': candidate_data.get('name', ''),
#                 'title': candidate_data.get('title', ''),
#                 'company': candidate_data.get('company', '')
#             })

#             # Step 3: Save results
#             print("\nSaving results...")
#             self.sheets.save_analysis(
#                 self.sheet_id,
#                 analysis,
#                 input_row_number=row_number
#             )

#             return True

#         except Exception as e:
#             print(f"Error processing candidate: {e}")
#             if row_number:
#                 self.sheets.mark_row_processed(self.sheet_id, row_number)
#             return False

#     def process_all(self, delay: Optional[float] = 2.0):
#         """Process all new candidates.
        
#         Args:
#             delay: Delay between processing candidates in seconds
#         """
#         print("\nStarting candidate processing...")
        
#         try:
#             total_processed = 0
#             total_success = 0
            
#             while True:
#                 candidates = self.sheets.get_candidates(self.sheet_id)
#                 if not candidates:
#                     break
                
#                 print(f"\nFound {len(candidates)} new candidates")
                
#                 for idx, candidate in enumerate(candidates, 1):
#                     print(f"\nProcessing {idx}/{len(candidates)}")
#                     success = self.process_candidate(candidate)
                    
#                     total_processed += 1
#                     if success:
#                         total_success += 1
                    
#                     if delay and idx < len(candidates):
#                         time.sleep(delay)

#             print(f"\nProcessing complete!")
#             print(f"Total processed: {total_processed}")
#             print(f"Successfully processed: {total_success}")

#         except KeyboardInterrupt:
#             print("\nProcess interrupted by user")
#         except Exception as e:
#             print(f"Error in processing loop: {e}")

# def main():
#     """Main entry point."""
#     print("\n=== Cerebras Candidate Processor ===")
#     try:
#         processor = CandidateProcessor()
#         processor.process_all()
#     except Exception as e:
#         print(f"\nError: {e}")

# if __name__ == "__main__":
#     main()



import os
import time
from typing import Dict, Optional
from dotenv import load_dotenv
from scraper import DataScraper
from sheet_handler import SheetHandler
from inference import Inference
from control_panel import ControlPanel

load_dotenv()

class CandidateProcessor:
    def __init__(self):
        """Initialize processor with all components."""
        self.control_panel = ControlPanel()
        self.scraper = DataScraper()
        self.sheets = SheetHandler(self.control_panel)
        self.inference = Inference(self.control_panel)
        self.sheet_id = os.getenv('SHEET_ID')
        
        if not self.sheet_id:
            raise ValueError("SHEET_ID environment variable is required")
            
        print("\nProcessor initialized with configuration:")
        print(f"Active prompt: {self.control_panel.config['inference_controls']['active_prompt']}")
        print(f"Sheet highlighting: {'enabled' if self.control_panel.should_highlight_rows() else 'disabled'}")
        input_sheet, output_sheet = self.control_panel.get_sheet_names()
        print(f"Using sheets: {input_sheet} → {output_sheet}")

    def process_candidate(self, candidate_data: Dict) -> bool:
        """Process a single candidate.
        
        Args:
            candidate_data: Dictionary containing candidate information
            
        Returns:
            bool: True if processing was successful
        """
        try:
            email = candidate_data.get('email', '').strip()
            linkedin = candidate_data.get('linkedin', '').strip()
            row_number = candidate_data.get('row_number')
            
            print(f"\nProcessing row {row_number}")
            print(f"LinkedIn: {linkedin or 'None'}")
            print(f"Email: {email or 'None'}")
            
            if not linkedin and not email:
                print("No LinkedIn or email - marking row as processed")
                if row_number and self.control_panel.should_highlight_rows():
                    self.sheets.mark_row_processed(self.sheet_id, row_number)
                return False

            # Step 1: Scrape data if enabled
            profile_data = ""
            company_data = ""
            if self.control_panel.config["scraping_controls"]["scan_for_linkedin"]:
                print("\nScraping data...")
                scrape_result = self.scraper.scrape(
                    linkedin_url=linkedin,
                    email=email
                )
                profile_data = scrape_result.get('linkedin_data', '')
                company_data = scrape_result.get('company_research', '')
            
            # Step 2: Run analysis
            print("\nAnalyzing candidate...")
            analysis = self.inference.analyze_candidate(
                profile_data=profile_data,
                company_data=company_data,
                email=email,
                linkedin_url=linkedin
            )

            # Step 3: Save results
            print(f"\nAnalysis complete - Priority: {analysis.get('priority', 'unknown')}")
            self.sheets.save_analysis(
                self.sheet_id,
                analysis,
                input_row_number=row_number
            )

            return True

        except Exception as e:
            print(f"Error processing candidate: {e}")
            if row_number and self.control_panel.should_highlight_rows():
                self.sheets.mark_row_processed(self.sheet_id, row_number)
            return False

    def process_all(self, batch_size: Optional[int] = None, delay: float = 2.0):
        """Process all new candidates.
        
        Args:
            batch_size: Optional number of candidates to process before stopping
            delay: Delay between processing candidates in seconds
        """
        try:
            total_processed = 0
            total_success = 0
            
            while True:
                candidates = self.sheets.get_candidates(self.sheet_id)
                if not candidates:
                    break
                    
                if batch_size:
                    candidates = candidates[:batch_size]
                
                print(f"\nProcessing batch of {len(candidates)} candidates")
                
                for idx, candidate in enumerate(candidates, 1):
                    print(f"\nCandidate {idx}/{len(candidates)}")
                    success = self.process_candidate(candidate)
                    
                    total_processed += 1
                    if success:
                        total_success += 1
                    
                    if delay and idx < len(candidates):
                        time.sleep(delay)
                        
                if batch_size and total_processed >= batch_size:
                    print(f"\nReached batch size limit of {batch_size}")
                    break

            print(f"\nProcessing complete!")
            print(f"Total processed: {total_processed}")
            print(f"Successfully processed: {total_success}")

        except KeyboardInterrupt:
            print("\nProcess interrupted by user")
        except Exception as e:
            print(f"Error in processing loop: {e}")

def list_prompts():
    """List available prompts in the system."""
    control_panel = ControlPanel()
    prompts = control_panel.list_available_prompts()
    
    print("\nAvailable prompts:")
    for name, description in prompts.items():
        print(f"- {name}: {description}")
        
def change_prompt(name: str):
    """Change the active prompt."""
    control_panel = ControlPanel()
    control_panel.set_active_prompt(name)

def toggle_highlighting():
    """Toggle row highlighting on/off."""
    control_panel = ControlPanel()
    current = control_panel.should_highlight_rows()
    control_panel.update_config("sheet_controls", "highlight_processed_rows", not current)
    print(f"Row highlighting: {'enabled' if not current else 'disabled'}")

def main():
    """Main entry point with argument handling."""
    import argparse
    parser = argparse.ArgumentParser(description='Process candidates from spreadsheet')
    parser.add_argument('--batch', type=int, help='Number of candidates to process')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between candidates')
    parser.add_argument('--list-prompts', action='store_true', help='List available prompts')
    parser.add_argument('--prompt', type=str, help='Change active prompt')
    parser.add_argument('--toggle-highlighting', action='store_true', help='Toggle row highlighting')
    
    args = parser.parse_args()
    
    if args.list_prompts:
        list_prompts()
        return
        
    if args.prompt:
        change_prompt(args.prompt)
        return
        
    if args.toggle_highlighting:
        toggle_highlighting()
        return

    print("\n=== Cerebras Candidate Processor ===")
    try:
        processor = CandidateProcessor()
        processor.process_all(batch_size=args.batch, delay=args.delay)
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()