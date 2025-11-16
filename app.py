"""
Fyers & Dhan Callback Service for Render.com

This service stores the Fyers auth code AND Dhan tokenId and exposes endpoints for retrieval/clearing.

Deploy this to Render.com and set as your redirect_uri for both Fyers and Dhan API dashboards.
"""

from flask import Flask, request, jsonify
import os
import time

app = Flask(__name__)

# In-memory storage for Fyers auth code/state and Dhan tokenId (persists for the lifetime of the service)
# For production, consider using Redis or a database
auth_storage = {
    "fyers": {
        "auth_code": None,
        "state": None,
        "timestamp": None,
    },
    "dhan": {
        "token_id": None,
        "timestamp": None,
    }
}

# ---------- FYERS CALLBACK & API ----------

@app.route('/callback')
def fyers_callback():
    """
    Fyers redirects here with auth_code and state as query parameters.
    We store them and display them on the page.
    """
    auth_code = request.args.get("auth_code")
    state_recv = request.args.get("state")
    
    # Store the Fyers auth code
    if auth_code:
        auth_storage["fyers"]["auth_code"] = auth_code
        auth_storage["fyers"]["state"] = state_recv
        auth_storage["fyers"]["timestamp"] = time.time()
    
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
    API endpoint to retrieve the stored Fyers auth code.
    Returns JSON with the auth code or error message.
    Also checks if code is fresh (not older than 3 minutes).
    """
    fyers_data = auth_storage["fyers"]
    if fyers_data["auth_code"]:
        # Check if code is fresh (auth codes expire quickly, typically within 1-2 minutes)
        current_time = time.time()
        code_age = current_time - fyers_data["timestamp"] if fyers_data["timestamp"] else float('inf')
        max_age_seconds = 180
        
        if code_age > max_age_seconds:
            return jsonify({
                "success": False,
                "message": f"Auth code expired (age: {int(code_age)}s, max: {max_age_seconds}s). Please login again.",
                "code_age": code_age
            }), 410  # 410 Gone - resource expired
        
        return jsonify({
            "success": True,
            "auth_code": fyers_data["auth_code"],
            "state": fyers_data["state"],
            "timestamp": fyers_data["timestamp"],
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
    Clear the stored Fyers auth code after successful use.
    This prevents reuse of already-used codes.
    """
    auth_storage["fyers"]["auth_code"] = None
    auth_storage["fyers"]["state"] = None
    auth_storage["fyers"]["timestamp"] = None
    return jsonify({
        "success": True,
        "message": "Fyers auth code cleared successfully"
    })

# ---------- DHAN CALLBACK & API ----------

@app.route('/callback/dhan')
def dhan_callback():
    """
    Dhan redirects here after user browser login,
    with tokenId as a query parameter in the URL (see docs).
    Example: /callback/dhan?tokenId=XXXXXXX
    """
    token_id = request.args.get("tokenId")
    store_time = time.time()
    
    # Store Dhan tokenId if present
    if token_id:
        auth_storage["dhan"]["token_id"] = token_id
        auth_storage["dhan"]["timestamp"] = store_time

    # Display on page for user/manual check
    return f"""
    <html>
        <head><title>Dhan tokenId</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>Dhan Authentication</h2>
            <p><strong>tokenId:</strong> {token_id or 'None'}</p>
            <p style="color: green;">✅ tokenId stored! Your script can now retrieve it automatically.</p>
            <p style="font-size: 13px; color: #888;">(Proceed to use tokenId in step 3 of the Dhan OAuth docs.)</p>
        </body>
    </html>
    """

@app.route('/get-dhan-token')
def get_dhan_token():
    """
    API endpoint to retrieve the stored Dhan tokenId.
    tokenId can be used to obtain an access token via Dhan APIs (app/consumeApp-consent).
    tokenIds expire quickly, so we set a freshness requirement (3 min).
    """
    dhan_data = auth_storage["dhan"]
    if dhan_data["token_id"]:
        current_time = time.time()
        code_age = current_time - dhan_data["timestamp"] if dhan_data["timestamp"] else float('inf')
        max_age_seconds = 180  # 3 min, adjust as needed per Dhan docs
        
        if code_age > max_age_seconds:
            return jsonify({
                "success": False,
                "message": f"tokenId expired (age: {int(code_age)}s, max: {max_age_seconds}s). Please login on Dhan again.",
                "code_age": code_age
            }), 410
        
        return jsonify({
            "success": True,
            "token_id": dhan_data["token_id"],
            "timestamp": dhan_data["timestamp"],
            "code_age_seconds": code_age
        })
    else:
        return jsonify({
            "success": False,
            "message": "No Dhan tokenId available yet. Complete the Dhan OAuth browser login first."
        }), 404

@app.route('/clear-dhan-token', methods=['POST', 'GET'])
def clear_dhan_token():
    """
    Clear the stored Dhan tokenId after successful use.
    """
    auth_storage["dhan"]["token_id"] = None
    auth_storage["dhan"]["timestamp"] = None
    return jsonify({
        "success": True,
        "message": "Dhan tokenId cleared successfully"
    })

# ---------- INDEX / HEALTH ----------

@app.route('/')
def index():
    """Health check endpoint with all available Redirect endpoints."""
    return jsonify({
        "status": "running",
        "endpoints": {
            "/callback": "Fyers redirect endpoint (stores auth code)",
            "/get-auth-code": "API to retrieve stored Fyers auth code (checks freshness)",
            "/clear-auth-code": "Clear stored Fyers auth code after use",
            "/callback/dhan": "Dhan redirect endpoint (stores tokenId)",
            "/get-dhan-token": "API to retrieve stored Dhan tokenId (checks freshness)",
            "/clear-dhan-token": "Clear stored Dhan tokenId after use"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

