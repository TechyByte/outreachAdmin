import os
import requests
from msal import ConfidentialClientApplication

# Load configuration from environment variables or a config file
CLIENT_ID = os.getenv("O365_CLIENT_ID")
CLIENT_SECRET = os.getenv("O365_CLIENT_SECRET")
TENANT_ID = os.getenv("O365_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]

class O365Interface:
    def __init__(self):
        self.app = ConfidentialClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            client_credential=CLIENT_SECRET
        )
        self.token = None

    def authenticate(self):
        """Authenticate and obtain an access token."""
        result = self.app.acquire_token_for_client(scopes=SCOPES)
        if "access_token" in result:
            self.token = result["access_token"]
        else:
            raise Exception(f"Authentication failed: {result.get('error_description')}")

    def get_headers(self):
        """Return headers for Graph API requests."""
        if not self.token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    def find_staff(self, query):
        """Search for staff members in the directory."""
        url = "https://graph.microsoft.com/v1.0/users"
        params = {"$filter": f"startswith(displayName, '{query}')"}
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()
        return response.json().get("value", [])

    def send_email(self, recipient, subject, body):
        """Send an email on behalf of the authenticated user."""
        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        email_data = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": recipient}}],
            },
            "saveToSentItems": "true",
        }
        response = requests.post(url, headers=self.get_headers(), json=email_data)
        response.raise_for_status()
        return response.status_code == 202

    def get_calendar_events(self):
        """Retrieve calendar events for the authenticated user."""
        url = "https://graph.microsoft.com/v1.0/me/events"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json().get("value", [])

    def create_calendar_event(self, subject, start_time, end_time, attendees):
        """Create a calendar event and send invites."""
        url = "https://graph.microsoft.com/v1.0/me/events"
        event_data = {
            "subject": subject,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
            "attendees": [{"emailAddress": {"address": email}, "type": "required"} for email in attendees],
        }
        response = requests.post(url, headers=self.get_headers(), json=event_data)
        response.raise_for_status()
        return response.json()
