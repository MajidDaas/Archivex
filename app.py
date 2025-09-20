# app.py
from flask import Flask, render_template, redirect, url_for, session, request, abort, jsonify
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import os

# Import configuration and utilities
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, TABS, get_user_access, USER_ROLES
from drive_utils import build_drive_service, search_files, upload_file

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'

# --- Configuration for local/production ---
def create_flow():
    # --- DYNAMICALLY DETERMINE REDIRECT URI BASED ON REQUEST ---
    # This fixes the "Working outside of request context" error
    host_url = request.host_url
    is_local = 'localhost' in host_url or '127.0.0.1' in host_url
    redirect_uri = (
        "http://localhost:5000/callback" if is_local
        else "https://majiddaas.pythonanywhere.com/callback" # Adjust for your production domain
    )
    
    print(f"[FLOW] Host URL: {host_url}, Is Local: {is_local}, Redirect URI: {redirect_uri}")

    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=[
            "openid",
            "email",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/drive.file"
        ],
        redirect_uri=redirect_uri
    )

# --- Routes ---
@app.route('/')
def index():
    # --- MAIN CHANGE: Render index.html directly, don't redirect to /login ---
    # The JavaScript will handle showing the auth section if not logged in.
    if 'email' not in session:
        # Pass demo_users so the template can show the demo login options
        return render_template('index.html', auth_url=None, demo_users=list(USER_ROLES.keys()))
    return render_template('index.html', auth_url=None)

# The /login route is still needed for the "Login with Google" button's JS logic
@app.route('/login')
def login():
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    print(f"[LOGIN] Auth URL: {authorization_url}")
    # Pass demo_users here too, in case someone navigates directly to /login
    return render_template('index.html', auth_url=authorization_url, demo_users=list(USER_ROLES.keys()))

@app.route('/callback')
def callback():
    if 'state' not in session:
        abort(400, description="State missing from session")
    request_state = request.args.get('state')
    if not request_state:
        abort(400, description="State missing from request URL")
    if session['state'] != request_state:
        abort(400, description="State mismatch")
    try:
        flow = create_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            Request(),
            GOOGLE_CLIENT_ID
        )
        session['email'] = id_info['email']
        session['google_token'] = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET
        }
        access = get_user_access(session['email'])
        if not access['tabs']:
            session.clear()
            # Pass demo_users for consistency if error page is shown via template
            return render_template('index.html', error="Access denied. No tabs assigned. Contact administrator.", demo_users=list(USER_ROLES.keys())), 403
        return redirect(url_for('index'))
    except Exception as e:
        print(f"[CALLBACK] OAuth failed: {e}")
        session.clear()
        # Pass demo_users for consistency if error page is shown via template
        return redirect(url_for('index', error="Authentication failed. Please try again.", demo_users=list(USER_ROLES.keys())))

@app.route('/logout')
def logout():
    email = session.get('email')
    session.clear()
    print(f"[LOGOUT] {email} logged out")
    # Redirect to index, which will now show the login page
    # Pass demo_users so the login page is shown correctly
    return redirect(url_for('index', demo_users=list(USER_ROLES.keys())))

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
        print(f"[API/FILES] Failed: {e}")
        return jsonify({"error": "Failed to load files from Google Drive"}), 500

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
        print(f"[API/UPLOAD] Failed: {e}")
        return jsonify({"error": "Upload failed"}), 500

# --- Error Handlers ---
@app.errorhandler(400)
def bad_request(e):
    # Pass demo_users for consistency
    return render_template('index.html', error=f"Bad Request: {getattr(e, 'description', 'Bad Request')}", demo_users=list(USER_ROLES.keys())), 400

@app.errorhandler(403)
def forbidden(e):
    # Pass demo_users for consistency
    return render_template('index.html', error="Forbidden. Access denied.", demo_users=list(USER_ROLES.keys())), 403

@app.errorhandler(404)
def not_found(e):
    # Pass demo_users for consistency
    return render_template('index.html', error="Page not found.", demo_users=list(USER_ROLES.keys())), 404

@app.errorhandler(500)
def internal_error(e):
    # Pass demo_users for consistency
    return render_template('index.html', error="Internal server error.", demo_users=list(USER_ROLES.keys())), 500

# --- Improved Demo Login Route ---
@app.route('/demo_login', methods=['GET', 'POST'])
def demo_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        print(f"[DEMO LOGIN] POST email: '{email}'")
        if email and email in USER_ROLES:
            session['email'] = email
            session['google_token'] = {
                'access_token': 'demo_access_token_placeholder',
                'refresh_token': 'demo_refresh_token_placeholder',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET
            }
            print(f"[DEMO LOGIN] Successful login for {email}")
            return redirect(url_for('index'))
        else:
            error_message = f"Demo login failed for '{email}'. Email not authorized."
            print(f"[DEMO LOGIN] {error_message}")
            # Pass demo_users so the login page is shown with options
            return render_template('index.html', error=error_message, auth_url=None, demo_users=list(USER_ROLES.keys()))

    # GET request - Redirect back to main index, which will show the login page with demo users
    print("[DEMO LOGIN] GET request, redirecting to index")
    return redirect(url_for('index', demo_users=list(USER_ROLES.keys())))

# --- Enable local running ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) # Use debug=False in production

