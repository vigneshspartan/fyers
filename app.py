"""
Fyers Callback Service for Render.com
This service stores the auth code and makes it accessible for automated retrieval.

Deploy this to Render.com and update your redirect_uri in the Fyers app dashboard.
"""

from flask import Flask, request, jsonify
import os
import time

app = Flask(__name__)

# In-memory storage for auth code (persists for the lifetime of the service)
# For production, consider using Redis or a database
auth_storage = {
    "auth_code": None,
    "state": None,
    "timestamp": None
}

@app.route('/callback')
def callback():
    """
    Fyers redirects here with auth_code and state as query parameters.
    We store them and display them on the page.
    """
    auth_code = request.args.get("auth_code")
    state_recv = request.args.get("state")
    
    # Store the auth code
    if auth_code:
        auth_storage["auth_code"] = auth_code
        auth_storage["state"] = state_recv
        auth_storage["timestamp"] = time.time()
    
    # Display on page (for manual viewing)
    return f"""
    <html>
        <head><title>Fyers Auth Code</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>Fyers Authentication</h2>
            <p><strong>Auth code:</strong> {auth_code or 'None'}</p>
            <p><strong>State:</strong> {state_recv or 'None'}</p>
            <p style="color: green;">✅ Code stored! Your script can now retrieve it automatically.</p>
        </body>
    </html>
    """

@app.route('/get-auth-code')
def get_auth_code():
    """
    API endpoint to retrieve the stored auth code.
    Returns JSON with the auth code or error message.
    """
    if auth_storage["auth_code"]:
        return jsonify({
            "success": True,
            "auth_code": auth_storage["auth_code"],
            "state": auth_storage["state"],
            "timestamp": auth_storage["timestamp"]
        })
    else:
        return jsonify({
            "success": False,
            "message": "No auth code available yet. Complete the Fyers login first."
        }), 404

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "endpoints": {
            "/callback": "Fyers redirect endpoint",
            "/get-auth-code": "API to retrieve stored auth code"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

