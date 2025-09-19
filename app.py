# app.py
from flask import Flask, render_template, redirect, url_for, session, request, abort, jsonify
# Import from google_auth_oauthlib.flow correctly
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import os
# import json # Not used in this snippet
# from io import BytesIO # Not used in this snippet

# Import configuration and utilities
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, TABS, get_user_access
from drive_utils import build_drive_service, search_files, upload_file

app = Flask(__name__)
# Use the secret key from config.py, which loads from environment variables
# Hardcoding it like this is less secure
app.secret_key = SECRET_KEY # Use the one from config

# ⚠️ ONLY FOR LOCAL DEVELOPMENT — REMOVE IN PRODUCTION
# This should ideally be handled by an environment check
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- Google OAuth2 Flow Setup ---
# --- FIX 1: Remove ALL trailing spaces from URLs and scopes ---
# --- FIX 2: Update redirect URIs for PythonAnywhere ---
flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            # --- FIX 1a: Removed trailing spaces ---
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",  # No trailing space
            "token_uri": "https://oauth2.googleapis.com/token",      # No trailing space
            # --- FIX 2a: Update redirect URI for PythonAnywhere ---
            "redirect_uris": ["https://majiddaas.pythonanywhere.com/callback"] # Match your domain
        }
    },
    scopes=[
        'openid',
        # --- FIX 1b: Removed trailing spaces from scopes ---
        'https://www.googleapis.com/auth/userinfo.email', # No trailing space
        'https://www.googleapis.com/auth/drive.file'    # No trailing space, Scope for uploading files
    ],
    # --- FIX 2b: Update redirect_uri for PythonAnywhere ---
    redirect_uri='https://majiddaas.pythonanywhere.com/callback' # Match your domain
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
    # --- RENDER index.html INSTEAD ---
    return render_template('index.html', auth_url=authorization_url)
    
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
        # It's better to flash a message or redirect to an error page
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

# Remove or comment out the if __name__ == '__main__' block for PythonAnywhere
# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)

@app.route('/demo_login', methods=['GET', 'POST'])
def demo_login():
    """
    Demo login route for testing without Google OAuth.
    Checks if the provided email is in the predefined USER_ROLES.
    """
    if request.method == 'POST':
        # 1. Get and sanitize the email from the form
        email = request.form.get('email', '').strip()

        # 2. Check if the email is authorized
        if email and email in USER_ROLES:
            # 3. Log the user in by setting session variables
            session['email'] = email
            # 4. Create a dummy google_token structure
            # This mimics the real token structure for access checks in get_user_access
            # but won't work for actual Drive API calls.
            session['google_token'] = {
                'access_token': 'demo_access_token_placeholder',
                'refresh_token': 'demo_refresh_token_placeholder',
                # --- CRITICAL FIX: Removed trailing spaces from token_uri ---
                'token_uri': 'https://oauth2.googleapis.com/token', # No trailing spaces
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET
            }
            print(f"✅ [DEMO] Login successful for {email}")
            # 5. Redirect to the main index page
            return redirect(url_for('index'))
        else:
            # 6. Handle failed login attempt
            error_message = f"Demo login failed for '{email}'. Email not authorized or not in USER_ROLES."
            print(f"❌ [DEMO] {error_message}")
            # Pass the error message to the template for display
            return render_template('index.html', error=error_message)

    # --- GET request handling ---
    # If someone navigates to /demo_login directly (GET), redirect to main page
    # The demo login form is already on index.html
    # Alternatively, you could render a separate template here.
    return redirect(url_for('index'))
# --- End of /demo_login route ---
