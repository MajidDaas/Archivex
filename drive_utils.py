# drive_utils.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
import tempfile
import os

def build_drive_service(token_info):
    credentials = Credentials(
        token=token_info['access_token'],
        refresh_token=token_info.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=token_info['client_id'],
        client_secret=token_info['client_secret']
    )
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)

def search_files(drive_service, folder_id, search_term=""):
    query = "mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    if search_term:
        escaped_term = search_term.replace("'", "\\'")
        query += f" and fullText contains '{escaped_term}'"

    # Include modifiedTime for display
    try:
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, mimeType, webViewLink, createdTime, modifiedTime)", # Added modifiedTime
            pageSize=50
        ).execute()
        return results.get('files', [])
    except Exception as e:
        print(f"An error occurred during search: {e}")
        return []

def upload_file(drive_service, file_stream, file_name, folder_id=None):
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(file_stream.read())
        tmp_file_path = tmp_file.name
    try:
        media = MediaFileUpload(tmp_file_path, resumable=True)
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        return file
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
