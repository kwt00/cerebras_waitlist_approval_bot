# import os
# import json
# from typing import Dict, Optional
# from cerebras.cloud.sdk import Cerebras
# from dotenv import load_dotenv

# load_dotenv()

# TEMPLATES = {
#     'student': """Dear {name},

# {custom_line}

# Based on your academic background, we'd love to have you join our event! You'll get to:
# - Work hands-on with Cerebras AI hardware
# - Build projects using our Inference API
# - Connect with AI researchers and engineers

# Next steps:
# 1. Register here: [LINK]
# 2. Join Discord: cerebras.ai/discord 
# 3. Review docs: [DOCS]

# Best regards,
# The Cerebras Team""",

#     'startup': """Dear {name},

# {custom_line}

# Your startup experience makes you an ideal participant. You'll have the opportunity to:
# - Build on enterprise-grade AI infrastructure  
# - Network with potential partners
# - Create scalable AI solutions

# Next steps:
# 1. Register here: [LINK]
# 2. Join Discord: cerebras.ai/discord
# 3. Book call: [CALENDAR]

# Best regards,
# The Cerebras Team""",

#     'enterprise': """Dear {name},

# {custom_line}

# Your experience at {company} aligns perfectly with our mission. We offer:
# - Hands-on access to Cerebras AI infrastructure
# - Direct connection with our technical team
# - Enterprise solution prototyping

# Next steps:
# 1. Register here: [LINK]
# 2. Join Discord: cerebras.ai/discord
# 3. Book call: [CALENDAR]

# Best regards,
# The Cerebras Team"""
# }

# class Inference:
#     def __init__(self):
#         self.client = Cerebras(api_key=os.getenv("CEREBRAS_KEY"))
#         self.model = "llama3.3-70b"

#     def analyze_candidate(self, profile_data: Optional[str], company_data: Optional[str], 
#                          email: Optional[str], linkedin_url: Optional[str] = None) -> Dict:
#         """Analyze candidate and generate response."""
#         try:
#             # Handle empty inputs
#             profile_text = str(profile_data) if profile_data else ""
#             company_text = str(company_data) if company_data else ""

#             # Initialize with reject by default
#             result = {
#                 "name": "",
#                 "title": "",
#                 "company": "",
#                 "location": "",
#                 "priority": "reject",
#                 "priority_reasoning": "",
#                 "email_draft": "",
#                 "email": email or "",
#                 "linkedin": linkedin_url or ""
#             }
            
#             # Skip if no data
#             if not profile_text.strip() and not company_text.strip():
#                 result["priority_reasoning"] = "* No profile information available\n* No data to analyze"
#                 return result
            
#             analysis = self._get_analysis(profile_text, company_text)
#             result.update(analysis)

#             # Generate email if accepted
#             if result['priority'] == 'accept':
#                 background = self._get_background_type(profile_text)
#                 accomplishment = self._get_custom_line(profile_text)
                
#                 custom_line = f"We are impressed with {accomplishment}"
#                 template = TEMPLATES.get(background, TEMPLATES['enterprise'])
                
#                 result['email_draft'] = template.format(
#                     name=result['name'] or 'there',
#                     custom_line=custom_line,
#                     company=result['company'] or 'your company'
#                 )
            
#             return result
            
#         except Exception as e:
#             print(f"Analysis failed: {e}")
#             return {
#                 "name": "",
#                 "title": "",
#                 "company": "",
#                 "location": "",
#                 "priority": "reject",
#                 "priority_reasoning": "* Error during analysis\n* System error occurred",
#                 "email_draft": "",
#                 "email": email or "",
#                 "linkedin": linkedin_url or ""
#             }

#     def _get_analysis(self, profile: str, company_info: str) -> Dict:
#         """Analyze candidate profile."""
#         prompt = f"""Analyze candidate for Cerebras event. BE SPECIFIC about why accepted/rejected.

# Profile: {profile}
# Company Info: {company_info}

# ACCEPT if ANY are true:
# - CEO/CTO/Founder at tech/AI company
# - Technical role at FAANG/big tech
# - Machine learning/AI research role
# - Currently leads technical team

# REJECT everyone else.

# Return strict JSON with reasoning:
# {{
#     "name": "", 
#     "title": "",
#     "company": "",
#     "location": "",
#     "priority": "accept/reject",
#     "priority_reasoning": "* [Specific reason 1]\\n* [Specific reason 2]"
# }}

# For accept, explain exact role/company.
# For reject, explain what criteria they missed."""

#         try:
#             response = self.client.chat.completions.create(
#                 messages=[
#                     {"role": "system", "content": "You are a strict technical evaluator that gives specific reasons for decisions."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 model=self.model,
#                 response_format={"type": "json_object"},
#                 temperature=0
#             )
            
#             result = json.loads(response.choices[0].message.content)
            
#             # Ensure we have reasoning
#             if not result.get('priority_reasoning'):
#                 result['priority_reasoning'] = "* No specific criteria met\n* Profile lacks required technical leadership"
                
#             return result
#         except:
#             return {
#                 "name": "",
#                 "title": "",
#                 "company": "",
#                 "location": "",
#                 "priority": "reject",
#                 "priority_reasoning": "* Analysis failed\n* Could not process profile"
#             }

#     def _get_background_type(self, profile: str) -> str:
#         """Get background type for email template."""
#         if not profile:
#             return 'enterprise'
            
#         prompt = f"""Profile: {profile}

# Return ONLY one word - student, startup, or enterprise:
# - student = current student/recent grad
# - startup = founder/early employee
# - enterprise = established company

# Return ONLY the word."""

#         try:
#             response = self.client.chat.completions.create(
#                 messages=[{"role": "user", "content": prompt}],
#                 model=self.model,
#                 temperature=0
#             )
            
#             result = response.choices[0].message.content.strip().lower()
#             return result if result in TEMPLATES else 'enterprise'
#         except:
#             return 'enterprise'

#     def _get_custom_line(self, profile: str) -> str:
#         """Get custom line for email."""
#         if not profile:
#             return "your background and potential"
            
#         prompt = f"""Profile: {profile}

# Write ONE short line about their most impressive achievement or skill. 
# Must be specific, under 10 words.
# Example: "leading the ML team at Google Cloud"

# Return ONLY the line, no quotes."""

#         try:
#             response = self.client.chat.completions.create(
#                 messages=[{"role": "user", "content": prompt}],
#                 model=self.model,
#                 temperature=0
#             )
            
#             return response.choices[0].message.content.strip()
#         except:
#             return "your background and potential"



import os
import json
from typing import Dict, Optional
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from control_panel import ControlPanel

load_dotenv()

class Inference:
    def __init__(self, control_panel: Optional[ControlPanel] = None):
        self.controls = control_panel or ControlPanel()
        self.client = Cerebras(api_key=os.getenv("CEREBRAS_KEY"))
        
        # Get model settings from control panel
        inference_controls = self.controls.config["inference_controls"]
        self.model = inference_controls.get("model", "llama3.3-70b")
        self.temperature = inference_controls.get("temperature", 0)

    def analyze_candidate(self, profile_data: Optional[str], company_data: Optional[str], 
                         email: Optional[str], linkedin_url: Optional[str] = None) -> Dict:
        """Analyze candidate and generate response."""
        try:
            # Handle empty inputs
            profile_text = str(profile_data) if profile_data else ""
            company_text = str(company_data) if company_data else ""

            # Get default values from control panel
            defaults = self.controls.config["response_format"]["default_values"]
            result = defaults.copy()
            
            # Add contact info
            result.update({
                "email": email or "",
                "linkedin": linkedin_url or ""
            })

            # Skip if no data
            if not profile_text.strip() and not company_text.strip():
                return result
            
            # Get analysis using active prompt
            analysis = self._get_analysis(profile_text, company_text)
            
            # Only include fields specified in output format
            field_format = self.controls.get_field_format()
            for field in list(analysis.keys()):
                if not field_format.get(field, False):
                    analysis.pop(field)

            result.update(analysis)

            # Generate email if enabled and accepted
            if (self.controls.config["response_format"].get("email_template", True) 
                and result['priority'] == 'accept'):
                result['email_draft'] = self._generate_email(
                    name=result.get('name', 'there'),
                    company=result.get('company', 'your company'),
                    profile=profile_text
                )
            
            return result
            
        except Exception as e:
            print(f"Analysis failed: {e}")
            return defaults

    def _get_analysis(self, profile: str, company_info: str) -> Dict:
        """Analyze candidate profile."""
        try:
            # Get active prompt template and format
            prompt = self.controls.get_prompt()
            prompt = prompt.format(profile=profile, company_info=company_info)

            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a strict technical evaluator that gives specific reasons for decisions."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=self.temperature
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Analysis error: {e}")
            return self.controls.config["response_format"]["default_values"].copy()

    def _generate_email(self, name: str, company: str, profile: str) -> str:
        """Generate email from template."""
        # Get email template from control panel
        template = self.controls.config.get("email_template", {}).get("accept", """
Dear {name},

We would love to have you join us! Your experience at {company} aligns perfectly with what we're looking for.

Next steps:
1. Register here: [LINK]
2. Join Discord: cerebras.ai/discord
3. Schedule call: [CALENDAR]

Best regards,
The Cerebras Team""")

        try:
            return template.format(
                name=name,
                company=company
            )
        except:
            return "Error generating email"