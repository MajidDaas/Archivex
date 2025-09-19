# app.py
from flask import Flask, render_template, redirect, url_for, session, request, abort, jsonify
# Import from google_auth_oauthlib.flow correctly
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import os
import json
from io import BytesIO

# Import configuration and utilities
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, TABS, get_user_access
from drive_utils import build_drive_service, search_files, upload_file

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ⚠️ ONLY FOR LOCAL DEVELOPMENT — REMOVE IN PRODUCTION
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- Google OAuth2 Flow Setup ---
# Corrected: No trailing spaces, scopes defined properly
flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",  # No trailing space
            "token_uri": "https://oauth2.googleapis.com/token",      # No trailing space
            "redirect_uris": ["http://localhost:5000/callback"]
        }
    },
    scopes=[
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/drive.file' # Scope for uploading files
    ],
    redirect_uri='http://localhost:5000/callback'
)

# --- Routes ---

@app.route('/')
def index():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login')
def login():
    # --- Corrected OAuth Flow ---
    # `flow.authorization_url()` generates the URL with `response_type=code`
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    print(f"🔐 [DEBUG] Generated Google Auth URL: {authorization_url}")
    return render_template('login.html', auth_url=authorization_url)

@app.route('/callback')
def callback():
    if 'state' not in session:
        abort(400, description="State parameter missing.")
    if session['state'] != request.args.get('state'):
        abort(400, description="State mismatch.")

    try:
        # --- Fetch Token and Get User Info ---
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        from google.oauth2 import id_token
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            Request(),
            GOOGLE_CLIENT_ID
        )

        # --- Store User Info and Credentials in Session ---
        session['email'] = id_info['email']
        # Include client_id and client_secret for drive_utils
        session['google_token'] = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET
        }

        # --- Check Access ---
        access = get_user_access(session['email'])
        if not access['tabs']:
            session.clear()
            return "Access denied. Contact administrator.", 403

        return redirect(url_for('index'))

    except Exception as e:
        print(f"❌ [ERROR] OAuth callback failed: {e}")
        session.clear()
        return "Authentication failed. Please try again.", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- JSON API Endpoints ---

@app.route('/api/user')
def api_user():
    if 'email' not in session:
        return jsonify({"authenticated": False})
    access = get_user_access(session['email'])
    return jsonify({
        "authenticated": True,
        "email": session['email'],
        "accessible_tabs": access['tabs'],
        "folder_map": access['folder_map']
    })

@app.route('/api/tabs')
def api_tabs():
    return jsonify(TABS)

@app.route('/api/tab/<tab_name>/files')
def api_tab_files(tab_name):
    if 'email' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    access = get_user_access(session['email'])
    if tab_name not in access['tabs']:
        return jsonify({"error": "Access denied"}), 403

    folder_id = access['folder_map'].get(tab_name)
    search_term = request.args.get('q', '').strip()

    try:
        drive_service = build_drive_service(session['google_token'])
        files = search_files(drive_service, folder_id, search_term)
        return jsonify({"files": files})
    except Exception as e:
        print(f"❌ [ERROR] Failed to search files: {e}")
        return jsonify({"error": "Failed to load files. Please try again."}), 500

@app.route('/api/tab/<tab_name>/upload', methods=['POST'])
def api_upload_file(tab_name):
    if 'email' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    access = get_user_access(session['email'])
    if tab_name not in access['tabs']:
        return jsonify({"error": "Access denied"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        drive_service = build_drive_service(session['google_token'])
        folder_id = access['folder_map'].get(tab_name)

        # Pass the file stream directly
        uploaded_file = upload_file(drive_service, file.stream, file.filename, folder_id)

        return jsonify({
            "success": True,
            "file": {
                "name": file.filename,
                "webViewLink": uploaded_file['webViewLink'],
                "id": uploaded_file['id']
            }
        })
    except Exception as e:
        print(f"❌ [ERROR] Upload failed: {e}")
        return jsonify({"error": "Upload failed. Please try again."}), 500

# --- Error Handlers ---

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Forbidden"}), 403

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

