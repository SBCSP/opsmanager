from flask import session, redirect, url_for, request, current_app
from functools import wraps
import msal

# Define a utility function to retrieve config values
def get_config_value(key, default=None):
    # Use the current_app proxy to access the app context
    with current_app.app_context():
        # Import AppConfig inside the function to avoid circular imports
        from database.models import AppConfig
        config_item = AppConfig.query.filter_by(key=key).first()
    return config_item.value if config_item else default

# Initialize the MSAL Confidential Client Application
def get_msal_app():
    # Retrieve Azure AD app registration details from the database
    client_id = get_config_value("CLIENT_ID")
    client_secret = get_config_value("CLIENT_SECRET")
    authority = get_config_value("AUTHORITY")
    
    # Create and return the MSAL Confidential Client Application
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret,
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_route', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def login():
    app = get_msal_app()
    # Generate the authorization request URL and redirect the user to it
    redirect_uri = get_config_value("REDIRECT_FORCE")
    auth_url = app.get_authorization_request_url(
        ["User.Read"],
        redirect_uri=redirect_uri,
    )
    return redirect(auth_url)

def authorized():
    app = get_msal_app()
    # Handle the authorization response
    code = request.args.get("code")
    redirect_uri = get_config_value("REDIRECT_FORCE")
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=redirect_uri,
    )
    if "error" in result:
        return "Login failed: " + result["error_description"]
    session["user"] = result.get("id_token_claims")
    return redirect(url_for("dashboard"))

def logout():
    # Clear the session
    session.clear()
    # Retrieve the post-logout redirect URI
    post_logout_redirect_uri = url_for("dashboard", _external=True)
    return redirect(
        f"https://login.microsoftonline.com/common/oauth2/logout?post_logout_redirect_uri={post_logout_redirect_uri}"
    )