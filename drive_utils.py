from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import tempfile
import os

def build_drive_service(credentials_dict):
    creds = Credentials(
        token=credentials_dict['access_token'],
        refresh_token=credentials_dict.get('refresh_token'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET')
    )
    return build('drive', 'v3', credentials=creds)

def search_files(drive_service, folder_id=None, query_text=None, max_results=50):
    q = "trashed = false"
    if folder_id:
        q += f" and '{folder_id}' in parents"
    if query_text:
        q += f" and fullText contains '{query_text}'"

    results = drive_service.files().list(
        q=q,
        fields="files(id, name, webViewLink, mimeType, modifiedTime, owners, size)",
        pageSize=max_results,
        orderBy="modifiedTime desc"
    ).execute()
    return results.get('files', [])

def upload_file(drive_service, file_stream, filename, folder_id=None):
    file_metadata = {'name': filename}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(file_stream, resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,webViewLink'
    ).execute()
    return file
