import os
import json
from typing import Dict, Optional
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

load_dotenv()

TEMPLATES = {
    'student': """Dear {name},

{custom_line}

Based on your academic background, we'd love to have you join our AI hackathon! You'll get to:
- Work hands-on with Cerebras AI hardware
- Build projects using our Inference API
- Connect with AI researchers and engineers

Next steps:
1. Complete registration: [LINK]
2. Join Discord: cerebras.ai/discord 
3. Review API docs: [DOCS]

Best regards,
The Cerebras Team""",

    'startup': """Dear {name},

{custom_line}

Your startup experience makes you an ideal participant for our AI hackathon. You'll have the opportunity to:
- Build on enterprise-grade AI infrastructure  
- Network with potential partners
- Create scalable AI solutions

Next steps:
1. Register your team: [LINK]
2. Join Discord: cerebras.ai/discord
3. Book intro call: [CALENDAR]

Best regards,
The Cerebras Team""",

    'enterprise': """Dear {name},

{custom_line}

Your experience at {company} aligns perfectly with our mission. Our hackathon offers:
- Hands-on access to Cerebras AI infrastructure
- Direct connection with our technical team
- Enterprise solution prototyping

Next steps:
1. Register your team: [LINK]
2. Join Discord: cerebras.ai/discord
3. Schedule solution review: [CALENDAR]

Best regards,
The Cerebras Team"""
}

class Inference:
    def __init__(self):
        self.client = Cerebras(api_key=os.getenv("CEREBRAS_KEY"))
        self.model = "llama3.3-70b"

    def analyze_candidate(self, profile_data: Optional[str], company_data: Optional[str], 
                         email: Optional[str], linkedin_url: Optional[str] = None, 
                         twitter_url: Optional[str] = None) -> Dict:
        """Analyze candidate and generate appropriate response with email if accepted."""
        try:
            # Handle empty/None inputs
            profile_text = str(profile_data) if profile_data is not None else ""
            company_text = str(company_data) if company_data is not None else ""

            base_data = {
                "name": "",
                "title": "",
                "company": "",
                "location": "",
                "category": "other",
                "priority": "review",
                "priority_reasoning": "",
                "email_draft": "",
                "email": email or "",
                "linkedin": linkedin_url or "",
                "twitter": twitter_url or ""
            }
            
            # Skip domain analysis for common email providers
            if email:
                domain = email.split('@')[-1].lower()
                common_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'}
                if domain in common_domains:
                    company_text = ""

            if not profile_text.strip() and not company_text.strip():
                base_data.update({
                    "priority": "review",
                    "priority_reasoning": "* No profile information available\n* Contact information preserved for manual review\n* Additional data required"
                })
                return base_data
            
            analysis = self._get_analysis(profile_text, company_text)

            base_data.update(analysis)

            for key in base_data:
                if base_data[key] is None:
                    base_data[key] = ""

            if base_data['priority'] == 'accept':
                background = self._get_background_type(profile_data)
                accomplishment = self._get_custom_line(profile_data)
                custom_line = f"We are very impressed with your accomplishments, especially {accomplishment}"
                template = TEMPLATES.get(background, TEMPLATES['enterprise'])
                
                base_data['email_draft'] = template.format(
                    name=base_data['name'] or 'there',
                    custom_line=custom_line,
                    company=base_data['company'] or 'your company'
                )
            
            return base_data
            
        except Exception as e:
            print(f"Analysis failed: {e}")
            return {
                "name": "",
                "title": "",
                "company": "",
                "location": "",
                "category": "other",
                "priority": "review",
                "priority_reasoning": "* Error during analysis\n* System error occurred\n* Manual review required",
                "email_draft": "",
                "email": email or "",
                "linkedin": linkedin_url or "",
                "twitter": twitter_url or ""
            }

    def _get_analysis(self, profile: str, company_info: str) -> Dict:
        """Get initial candidate analysis with an inclusive approach."""
        prompt = f"""Analyze this candidate for the Cerebras AI Hackathon.

Profile: {profile}
Company: {company_info}

STRICT FORMAT RULES:
1. Fields MUST be "" (empty string) if not explicitly found in the data
2. Do NOT make assumptions or guess any information
3. Priority reasoning must be 2-3 bullet points starting with *
4. Only include factual, observed information

EVALUATION CRITERIA:
- ACCEPT if showing any signs of:
  * Software development experience
  * ML/AI experience or strong interest
  * Data science background
  * Technical research experience
  * Computer science education
- REVIEW if:
  * Background is unclear but hints at technical skills
  * Non-technical but shows strong project work
  * Limited information available
- REJECT only if clearly non-technical with no relevant experience

Return this exact JSON structure:
{{
    "name": "",  // MUST be "" if not explicitly found
    "title": "", // MUST be "" if not explicitly found
    "company": "", // MUST be "" if not explicitly found
    "location": "", // MUST be "" if not explicitly found
    "category": "engineer/researcher/product/business/other",
    "priority": "accept/review/reject",
    "priority_reasoning": "* [key fact 1]\\n* [key fact 2]\\n* [key fact 3]"
}}

Example good priority_reasoning:
* 5 years software engineering experience
* Currently works on ML team at Google
* Led development of recommendation system

Example bad priority_reasoning:
* Seems very qualified
* Has good experience
* Would be a great fit

Remember: Empty string ("") is REQUIRED when information is not explicitly present."""

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a technical evaluator that only outputs valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0
            )
            
            return json.loads(response.choices[0].message.content)
        except:
            return {
                "name": "",
                "title": "",
                "company": "",
                "location": "",
                "category": "other",
                "priority": "review",
                "priority_reasoning": "* Analysis failed\n* Could not process profile\n* Manual review needed"
            }

    def _get_background_type(self, profile: str) -> str:
        """Classify candidate as student, startup, or enterprise."""
        prompt = f"""Classify this profile as one of: student, startup, enterprise
Profile: {profile}
Return ONLY one word from the options above.

Guidelines:
- student: Currently in school or recent graduate
- startup: Founder, early employee, or small company
- enterprise: Established company employee

Return ONLY the single word classification."""

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a classifier that returns one word only."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip().lower()
            return result if result in TEMPLATES else 'enterprise'
        except:
            return 'enterprise'

    def _get_custom_line(self, profile: str) -> str:
        """Generate one custom line about candidate's unique value."""
        prompt = f"""Based on this profile, complete the following sentence about the candidate's most impressive technical accomplishment or skill:

Profile: {profile}

Complete this sentence:
"your [specific technical skill, project, or achievement]"

Guidelines:
- Must be specific and technical (e.g., "your development of machine learning models for fraud detection" NOT "your impressive background")
- Focus on their strongest technical accomplishment
- If profile lacks specific achievements, focus on their most relevant technical skill
- Keep response under 15 words
- Do not include quotes or prefixes
- Do not repeat the prompt format

Example good responses:
- development of scalable cloud infrastructure at Amazon
- research in computer vision at Stanford's AI Lab
- contributions to open-source machine learning projects

Example bad responses:
- impressive background in technology
- various technical achievements
- leadership abilities"""

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You write one specific, technical sentence."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0
            )
            
            return response.choices[0].message.content.strip()
        except:
            return "technical background and experience"