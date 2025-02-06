import os
import time
import re
from typing import Dict, Optional
from dotenv import load_dotenv
from scraper import DataScraper
from sheet_handler import SheetHandler
from inference import Inference
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput

load_dotenv()

class CandidateProcessor:
    def __init__(self):
        self.scraper = DataScraper()
        self.sheets = SheetHandler()
        self.inference = Inference()
        self.sheet_id = os.getenv('SHEET_ID')
        self.hubspot = HubSpot(access_token=os.getenv('HUBSPOT_ACCESS_TOKEN'))

    def generate_summary(self, analysis: Dict) -> str:
        """Have the LLM generate a compelling summary for HubSpot."""
        prompt = f"""Create a compelling professional summary for this candidate:
Name: {analysis.get('name')}
Title: {analysis.get('title')}
Company: {analysis.get('company')}
Background: {analysis.get('priority_reasoning')}

Format: Focus on their professional experience, technical skills, and potential contribution to AI/ML projects.
Tone: Professional and enthusiastic.
Length: 2-3 sentences maximum."""

        try:
            response = self.inference.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You write concise, professional summaries."},
                    {"role": "user", "content": prompt}
                ],
                model=self.inference.model,
                temperature=0
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating summary: {e}")
            return analysis.get('priority_reasoning', '')

    def sync_to_hubspot(self, analysis: Dict) -> bool:
        """Sync accepted candidate to HubSpot."""
        try:
            summary = self.generate_summary(analysis)
            print("\nGenerated Summary for HubSpot:")
            print(summary)

            properties = {
                "email": analysis.get('email'),
                "full_name": analysis.get('name'),
                "personal_summary": summary,
                "hs_linkedin_url": analysis.get('linkedin')
            }
            
            print("\nSending to HubSpot:")
            for key, value in properties.items():
                print(f"{key}: {value}")

            simple_public_object_input = SimplePublicObjectInput(properties=properties)
            
            contact = self.hubspot.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )
            
            print("\n✓ Contact synced to HubSpot")
            print(f"Contact ID: {contact.id}")
            return True
            
        except Exception as e:
            print(f"⚠️ HubSpot sync failed: {str(e)}")
            return False

    def process_candidate(self, candidate_data: Dict) -> bool:
        """Process a single candidate with full error handling."""
        try:
            email = candidate_data.get('email')
            linkedin = candidate_data.get('linkedin')
            row_data = candidate_data.get('row_data', [])
            
            identifier = email or linkedin or "Unknown"
            print(f"\nProcessing candidate: {identifier}")
            print("LINKED URL: "+str(linkedin if linkedin else ""))
            print("EMAIL: "+str(email if email else ""))
            
            if not linkedin and not email:
                print("No LinkedIn or email found - skipping")
                return False

            print("Scraping data...")
            scrape_result = self.scraper.scrape(linkedin_url=linkedin, email=email)
            
            print("Running analysis...")
            analysis = self.inference.analyze_candidate(
                profile_data=scrape_result.get('linkedin_data'),
                company_data=scrape_result.get('domain_data'),
                email=email
            )

            analysis.update({
                'email': email,
                'linkedin': linkedin,
                'twitter': ''
            })
            
            if self.sheet_id:
                print("Saving results...")
                self.sheets.save_analysis(self.sheet_id, analysis)
            else:
                print("No sheet ID configured")
                return False

            print("\nAnalysis Results:")
            for key, value in analysis.items():
                print(f"{key}: {value}")

            if analysis.get('priority') == 'accept':
                print("\nCandidate accepted - syncing to HubSpot...")
                if not analysis.get('email') or not analysis.get('linkedin'):
                    print("⚠️ Warning: Missing email or LinkedIn URL")
                    print(f"Email: {analysis.get('email')}")
                    print(f"LinkedIn: {analysis.get('linkedin')}")
                
                hubspot_success = self.sync_to_hubspot(analysis)
                if hubspot_success:
                    print("✓ Successfully synced to HubSpot")
                else:
                    print("⚠️ Failed to sync to HubSpot")

            print(f"\nComplete - Priority: {analysis.get('priority', 'unknown')}")
            if analysis.get('priority') == 'accept':
                print("✓ Invitation email generated")
            return True

        except Exception as e:
            print(f"Error processing candidate: {e}")
            return False

    def process_all(self, manual_confirm=True):
        """Process all new candidates from input sheet."""
        if not self.sheet_id:
            print("No sheet ID configured")
            return

        while True:
            try:
                candidates = self.sheets.get_candidates(self.sheet_id)
                
                if not candidates:
                    print("\nNo new candidates to process")
                    break
                
                print(f"\nFound {len(candidates)} new candidates to process")
                
                for idx, candidate in enumerate(candidates, 1):
                    print(f"\n--- Processing {idx}/{len(candidates)} ---")
                    
                    if manual_confirm:
                        input(f"Press Enter to process candidate {idx}...")
                    
                    success = self.process_candidate(candidate)
                    
                    if idx < len(candidates):
                        time.sleep(2)  # Rate limiting
                
                if not manual_confirm:
                    break
                    
                should_continue = input("\nContinue searching for new candidates? (y/n): ").lower()
                if should_continue != 'y':
                    break

            except KeyboardInterrupt:
                print("\nProcess interrupted by user")
                break
            except Exception as e:
                print(f"\nError in processing loop: {e}")
                choice = input("\nTry to continue? (y/n): ").lower()
                if choice != 'y':
                    break

def main():
    """Main execution with error handling."""
    print("\n=== Cerebras Hackathon Candidate Processor ===")
    
    try:
        processor = CandidateProcessor()
        # Set manual_confirm=False to remove manual steps
        processor.process_all(manual_confirm=True)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        print("\nProcessing complete")

if __name__ == "__main__":
    main()