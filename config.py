# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# --- Load configuration from environment variables ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")

# --- Define User Access and Tabs ---
# Format: { "user@example.com": ["tab1", "tab2", ...] }
USER_ROLES = {
    "admin@example.com": ["meeting_minutes", "elections", "members"],
    "elections-team@example.com": ["elections"],
    "minutes-team@example.com": ["meeting_minutes"],
    "GMan.GM725@gmail.com": ["meeting_minutes", "elections", "members"],
    # Add more users and their tabs here
}

# Format: { "tab_key": "Display Name" }
TABS = {
    "meeting_minutes": "Meeting Minutes",
    "elections": "Elections Archive",
    "members": "Members Data"
}

# Optional: Map tabs to Google Drive folder IDs for scoping searches/uploads
# Format: { "tab_key": "GOOGLE_DRIVE_FOLDER_ID" }
DRIVE_FOLDER_IDS = {
    "meeting_minutes": "YOUR_DRIVE_FOLDER_ID_1", # Replace with actual ID
    "elections": "YOUR_DRIVE_FOLDER_ID_2",       # Replace with actual ID
    "members": "YOUR_DRIVE_FOLDER_ID_3"          # Replace with actual ID
}

def get_user_access(email):
    """
    Retrieves accessible tabs and folder map for a given user email.
    """
    tabs = USER_ROLES.get(email, [])
    folder_map = {tab: DRIVE_FOLDER_IDS.get(tab) for tab in tabs if tab in DRIVE_FOLDER_IDS}
    return {
        'tabs': tabs,
        'folder_map': folder_map
    }

