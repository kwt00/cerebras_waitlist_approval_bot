import json
import os
from typing import Dict, Any, Optional, Tuple

class ControlPanel:
    def __init__(self, config_path: str = "control_panel.json"):
        """Initialize control panel with configuration file."""
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                print(f"Config file not found at {self.config_path}, using defaults")
                return self._get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration."""
        return {
            "sheet_controls": {
                "highlight_processed_rows": True,
                "highlight_color": {
                    "red": 0.95,
                    "green": 0.95,
                    "blue": 0.95
                },
                "input_sheet_name": "Sheet1",
                "output_sheet_name": "Sheet2",
                "write_headers": True
            },
            "inference_controls": {
                "active_prompt": "startup_ceo",
                "model": "llama3.3-70b",
                "temperature": 0,
                "prompts": {
                    "startup_ceo": {
                        "description": "Look for startup CEOs and tech leaders",
                        "text": "Analyze candidate for Cerebras event. BE SPECIFIC about why accepted/rejected.\n\nProfile: {profile}\nCompany Info: {company_info}\n\nACCEPT if ANY are true:\n- CEO/CTO/Founder at tech/AI company\n- Technical role at FAANG/big tech\n- Machine learning/AI research role\n- Currently leads technical team\n\nREJECT everyone else.\n\nReturn this exact JSON structure:\n{{\n    \"name\": \"\",\n    \"title\": \"\",\n    \"company\": \"\",\n    \"location\": \"\",\n    \"priority\": \"accept/reject\",\n    \"priority_reasoning\": \"* [Specific reason 1]\\n* [Specific reason 2]\"\n}}",
                        "output_format": {
                            "name": true,
                            "title": true,
                            "company": true,
                            "location": true,
                            "priority": true,
                            "priority_reasoning": true
                        }
                    }
                }
            },
            "response_format": {
                "required_fields": [
                    "name",
                    "email",
                    "linkedin",
                    "priority",
                    "priority_reasoning"
                ],
                "email_template": true,
                "default_values": {
                    "name": "",
                    "title": "",
                    "company": "",
                    "location": "",
                    "priority": "reject",
                    "priority_reasoning": "* No specific criteria met\n* Profile lacks required qualifications"
                }
            },
            "scraping_controls": {
                "scan_for_linkedin": true,
                "research_companies": true,
                "common_domains": [
                    "gmail.com",
                    "yahoo.com",
                    "hotmail.com",
                    "outlook.com"
                ]
            }
        }

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print("Configuration saved successfully")
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_config(self, section: str, key: str, value: Any):
        """Update a specific configuration value."""
        if section in self.config and key in self.config[section]:
            self.config[section][key] = value
            self.save_config()
            print(f"Updated {section}.{key} to {value}")
        else:
            print(f"Invalid section or key: {section}.{key}")

    def get_prompt(self) -> str:
        """Get the active prompt template."""
        controls = self.config["inference_controls"]
        active_prompt = controls["active_prompt"]
        return controls["prompts"][active_prompt]["text"]

    def should_highlight_rows(self) -> bool:
        """Check if row highlighting is enabled."""
        return self.config["sheet_controls"]["highlight_processed_rows"]

    def get_sheet_names(self) -> Tuple[str, str]:
        """Get configured sheet names."""
        controls = self.config["sheet_controls"]
        return (controls["input_sheet_name"], controls["output_sheet_name"])

    def get_required_fields(self) -> list:
        """Get list of required fields for responses."""
        return self.config["response_format"]["required_fields"]

    def get_highlight_color(self) -> Dict:
        """Get row highlight color configuration."""
        return self.config["sheet_controls"].get("highlight_color", {
            "red": 0.95,
            "green": 0.95,
            "blue": 0.95
        })

    def get_active_prompt_config(self) -> Dict:
        """Get active prompt configuration."""
        controls = self.config["inference_controls"]
        active_prompt = controls["active_prompt"]
        return controls["prompts"][active_prompt]

    def get_field_format(self) -> Dict[str, bool]:
        """Get which fields should be included in output."""
        active_config = self.get_active_prompt_config()
        return active_config["output_format"]

    def list_available_prompts(self) -> Dict[str, str]:
        """Get list of available prompts with descriptions."""
        prompts = self.config["inference_controls"]["prompts"]
        return {name: data["description"] for name, data in prompts.items()}

    def set_active_prompt(self, name: str):
        """Set the active prompt template."""
        if name in self.config["inference_controls"]["prompts"]:
            self.config["inference_controls"]["active_prompt"] = name
            self.save_config()
            print(f"Active prompt set to: {name}")
        else:
            print(f"Prompt '{name}' not found")

    def add_new_prompt(self, name: str, description: str, prompt_text: str, output_format: Dict[str, bool]):
        """Add a new prompt template."""
        if name in self.config["inference_controls"]["prompts"]:
            print(f"Prompt '{name}' already exists")
            return

        self.config["inference_controls"]["prompts"][name] = {
            "description": description,
            "text": prompt_text,
            "output_format": output_format
        }
        self.save_config()
        print(f"Added new prompt template: {name}")