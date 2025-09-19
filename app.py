# app.py
from flask import Flask, render_template, redirect, url_for, session, request, abort, jsonify
# Import from google_auth_oauthlib.flow correctly
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token  # Import id_token at the top
import os
# import json # Not used in this snippet
# from io import BytesIO # Not used in this snippet

# Import configuration and utilities
# Ensure USER_ROLES is imported for demo_login
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, TABS, get_user_access, USER_ROLES
from drive_utils import build_drive_service, search_files, upload_file

app = Flask(__name__)
# Use the secret key from config.py, which loads from environment variables
app.secret_key = SECRET_KEY
# Set session type (optional but can help)
app.config['SESSION_TYPE'] = 'filesystem'

# ⚠️ ONLY FOR LOCAL DEVELOPMENT — REMOVE IN PRODUCTION
# This should ideally be handled by an environment check
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- Google OAuth2 Flow Setup ---
# --- CRITICAL FIXES APPLIED:
# 1. REMOVE ALL TRAILING SPACES from URLs, scopes, and redirect URIs
#    This fixes the "Required parameter is missing: response_type" error.
# 2. Ensure redirect URIs match your PythonAnywhere domain
flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            # --- FIX 1a: Removed ALL trailing spaces from auth_uri and token_uri ---
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",  # No trailing spaces
            "token_uri": "https://oauth2.googleapis.com/token",      # No trailing spaces
            # --- FIX 2a: Update redirect URI for PythonAnywhere, No trailing spaces ---
            "redirect_uris": ["https://majiddaas.pythonanywhere.com/callback"] # Match your domain
        }
    },
    scopes=[
        'openid',
        # --- FIX 1b: Removed ALL trailing spaces from scopes ---
        'https://www.googleapis.com/auth/userinfo.email', # No trailing spaces
        'https://www.googleapis.com/auth/drive.file'    # No trailing spaces, Scope for uploading files
    ],
    # --- FIX 2b: Update redirect_uri for PythonAnywhere, No trailing spaces ---
    redirect_uri='https://majiddaas.pythonanywhere.com/callback' # Match your domain
)

# --- Routes ---

@app.route('/')
def index():
    if 'email' not in session:
        # FIX: Pass auth_url=None to prevent Undefined error in template
        # when user is not logged in and index.html is rendered without
        # coming from the /login route.
        return redirect(url_for('login'))
    # FIX: Pass auth_url=None to prevent Undefined error in template
    # when user is logged in.
    return render_template('index.html', auth_url=None)

@app.route('/login')
def login():
    # --- Corrected OAuth Flow ---
    # `flow.authorization_url()` generates the URL with `response_type=code`
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    print(f"🔐 [LOGIN] Generated Google Auth URL: {authorization_url}")
    print(f"🔐 [LOGIN] State generated and stored in session: {state}")
    # --- RENDER index.html and pass the auth_url ---
    return render_template('index.html', auth_url=authorization_url)

@app.route('/callback')
def callback():
    print(f"🔍 [CALLBACK] Callback accessed. Request args: {request.args}")
    print(f"🔍 [CALLBACK] Current session contents: {dict(session)}")

    # --- Check for 'state' in session ---
    if 'state' not in session:
        print("❌ [CALLBACK] ABORT: 'state' parameter missing from session!")
        abort(400, description="State parameter missing from session.")
    
    # --- Get 'state' from request args ---
    request_state = request.args.get('state')
    if not request_state:
        print("❌ [CALLBACK] ABORT: 'state' parameter missing from request URL!")
        abort(400, description="State parameter missing from request URL.")

    # --- Compare states ---
    session_state = session['state']
    if session_state != request_state:
        print(f"❌ [CALLBACK] ABORT: State mismatch! Session: {session_state}, Request: {request_state}")
        abort(400, description="State mismatch between session and request.")

    print("✅ [CALLBACK] State validation passed.")

    try:
        # --- Fetch Token and Get User Info ---
        print(f"🔄 [CALLBACK] Fetching token with URL: {request.url}")
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        print("✅ [CALLBACK] Token fetched successfully.")

        # Verify ID token
        print("🔍 [CALLBACK] Verifying ID token...")
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            Request(),
            GOOGLE_CLIENT_ID
        )
        print(f"✅ [CALLBACK] ID token verified. User: {id_info.get('email')}")

        # --- Store User Info and Credentials in Session ---
        session['email'] = id_info['email']
        # Include client_id and client_secret for drive_utils
        session['google_token'] = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET
        }
        print(f"💾 [CALLBACK] User session data stored for {session['email']}")

        # --- Check Access ---
        access = get_user_access(session['email'])
        print(f"🛂 [CALLBACK] User access checked: {access}")
        if not access['tabs']:
            print(f"🚫 [CALLBACK] Access denied for {session['email']}. Clearing session.")
            session.clear()
            return "Access denied. Contact administrator.", 403

        print(f"✅ [CALLBACK] Successful login for {session['email']}. Redirecting to index.")
        return redirect(url_for('index'))

    except Exception as e:
        print(f"❌ [CALLBACK] OAuth callback failed: {e}")
        # It's better to flash a message or redirect to an error page
        session.clear()
        # Redirect back to index with an error message (handled by template or JS)
        return redirect(url_for('index', error="Authentication failed. Please try again."))

@app.route('/logout')
def logout():
    email = session.get('email')
    session.clear()
    print(f"👋 [LOGOUT] User {email} logged out.")
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
        print(f"❌ [API/FILES] Failed to search files: {e}")
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
        print(f"❌ [API/UPLOAD] Upload failed: {e}")
        return jsonify({"error": "Upload failed. Please try again."}), 500

# --- Error Handlers ---

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Forbidden"}), 403

@app.errorhandler(400)
def bad_request(e):
    # Provide a more detailed error message for debugging
    description = getattr(e, 'description', 'Bad Request')
    print(f"🚨 [ERROR 400] {description}")
    return jsonify({"error": f"Bad Request: {description}"}), 400

# --- Demo Login Route ---

@app.route('/demo_login', methods=['GET', 'POST'])
def demo_login():
    """
    Demo login route for testing without Google OAuth.
    Checks if the provided email is in the predefined USER_ROLES.
    """
    if request.method == 'POST':
        # 1. Get and sanitize the email from the form
        email = request.form.get('email', '').strip()
        print(f"🔍 [DEMO LOGIN] POST request received for email: '{email}'")

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
            print(f"✅ [DEMO LOGIN] Successful login for {email}")
            # 5. Redirect to the main index page
            return redirect(url_for('index'))
        else:
            # 6. Handle failed login attempt
            error_message = f"Demo login failed for '{email}'. Email not authorized or not in USER_ROLES."
            print(f"❌ [DEMO LOGIN] {error_message}")
            # Pass the error message to the template for display
            # Also pass auth_url=None to prevent template errors
            return render_template('index.html', error=error_message, auth_url=None)

    # --- GET request handling ---
    # If someone navigates to /demo_login directly (GET), redirect to main page
    print("↩️ [DEMO LOGIN] GET request, redirecting to index.")
    return redirect(url_for('index'))

# Remove or comment out the if __name__ == '__main__' block for PythonAnywhere
# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)

