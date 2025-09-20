# config.py
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")

# IMPORTANT: Replace these with your actual Google Drive Folder IDs
DRIVE_FOLDER_IDS = {
    "meeting_minutes": "1q7NSOEGeA_8fqUANfWXzgrR8wKCLD4Gj",
    "elections": "YOUR_ELECTIONS_FOLDER_ID",
    "members": "YOUR_MEMBERS_FOLDER_ID"
}

USER_ROLES = {
    "admin@example.com": ["meeting_minutes", "elections", "members"],
    "elections-team@example.com": ["elections"],
    "minutes-team@example.com": ["meeting_minutes"],
    "GMan.GM725@gmail.com": ["meeting_minutes", "elections", "members"],
    # Add more users for testing
    "test1@example.com": ["meeting_minutes"],
    "test2@example.com": ["elections", "members"],
}

TABS = {
    "meeting_minutes": "Meeting Minutes",
    "elections": "Elections Archive",
    "members": "Members Data"
}

def get_user_access(email):
    tabs = USER_ROLES.get(email, [])
    folder_map = {tab: DRIVE_FOLDER_IDS.get(tab) for tab in tabs if tab in DRIVE_FOLDER_IDS}
    return {
        'tabs': tabs,
        'folder_map': folder_map
    }
