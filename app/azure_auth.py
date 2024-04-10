from flask import session, redirect, url_for, request
from functools import wraps
import msal
import os

# Load Azure AD app registration details
client_id = os.getenv("CLIENT_ID")  # Azure AD App Registration client id
client_secret = os.getenv("CLIENT_SECRET")  # Azure AD App Registration client secret
authority = os.getenv("AUTHORITY")  # Azure AD Tenant endpoint
redirect_path = "/authorized"  # Redirect URI after successful login

# Initialize the MSAL Confidential Client Application
app = msal.ConfidentialClientApplication(
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
    # Generate the authorization request URL and redirect the user to it
    auth_url = app.get_authorization_request_url(
        ["User.Read"],
        redirect_uri=os.getenv("REDIRECT_FORCE"),
        # redirect_uri=url_for("authorized_route", _external=True),
    )
    return redirect(auth_url)

def authorized():
    # Handle the authorization response
    code = request.args.get("code")
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=os.getenv("REDIRECT_FORCE"),
        # redirect_uri=url_for("authorized_route", _external=True),
    )
    if "error" in result:
        return "Login failed: " + result["error_description"]
    session["user"] = result.get("id_token_claims")
    return redirect(url_for("dashboard"))

def logout():
    # Clear the session
    session.clear()
    return redirect(
        "https://login.microsoftonline.com/common/oauth2/logout?post_logout_redirect_uri=" +
        url_for("dashboard", _external=True)
    )