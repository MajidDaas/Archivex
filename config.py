import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
CONFIG_PATH = os.path.join(INSTANCE_DIR, 'config.json')

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()
TEAMS = CONFIG['teams']
USER_TEAMS = CONFIG['user_teams']
TABS = CONFIG['tabs']

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")

def get_user_access(email):
    """Returns {tabs: [...], folders: {...}} for user"""
    user_teams = USER_TEAMS.get(email, [])
    accessible_tabs = set()
    folder_map = {}

    for team_key in user_teams:
        team = TEAMS.get(team_key, {})
        for tab in team.get('accessible_tabs', []):
            accessible_tabs.add(tab)
            if 'drive_folder_id' in team:
                folder_map[tab] = team['drive_folder_id']

    return {
        'tabs': list(accessible_tabs),
        'folder_map': folder_map
    }
