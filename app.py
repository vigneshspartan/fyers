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
    Also checks if code is fresh (not older than 5 minutes).
    """
    if auth_storage["auth_code"]:
        # Check if code is fresh (auth codes expire quickly, typically within 1-2 minutes)
        current_time = time.time()
        code_age = current_time - auth_storage["timestamp"] if auth_storage["timestamp"] else float('inf')
        
        # Fyers auth codes typically expire in 60-120 seconds, so we'll use 3 minutes as max age
        max_age_seconds = 180
        
        if code_age > max_age_seconds:
            return jsonify({
                "success": False,
                "message": f"Auth code expired (age: {int(code_age)}s, max: {max_age_seconds}s). Please login again.",
                "code_age": code_age
            }), 410  # 410 Gone - resource expired
        
        return jsonify({
            "success": True,
            "auth_code": auth_storage["auth_code"],
            "state": auth_storage["state"],
            "timestamp": auth_storage["timestamp"],
            "code_age_seconds": code_age
        })
    else:
        return jsonify({
            "success": False,
            "message": "No auth code available yet. Complete the Fyers login first."
        }), 404

@app.route('/clear-auth-code', methods=['POST', 'GET'])
def clear_auth_code():
    """
    Clear the stored auth code after successful use.
    This prevents reuse of already-used codes.
    """
    auth_storage["auth_code"] = None
    auth_storage["state"] = None
    auth_storage["timestamp"] = None
    return jsonify({
        "success": True,
        "message": "Auth code cleared successfully"
    })

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "endpoints": {
            "/callback": "Fyers redirect endpoint (stores auth code)",
            "/get-auth-code": "API to retrieve stored auth code (checks freshness)",
            "/clear-auth-code": "Clear stored auth code after use"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

