import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

url = "https://api.retool.com/v1/workflows/2d164f23-9959-4063-ab83-8abb73dcfe79/startTrigger"


api_key = os.getenv("RETOOL_KEY")


headers = {
    "Content-Type": "application/json",
    "X-Workflow-Api-Key": api_key
}

email_payload = {
    "recipient": "kevin.taylor1924@gmail.com",
    "subject": "Test Email from Retool API", 
    "body": "Hello, this is a test email sent via Retool API. Check out the <a href='https://cerebras.ai/discord'>Cerebras Discord</a>"  # Body of the email
}

response = requests.post(url, headers=headers, data=json.dumps(email_payload))

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")