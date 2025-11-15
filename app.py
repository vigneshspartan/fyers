from flask import Flask, request
import threading

app = Flask(__name__)

# Global variable to store auth_code
auth_data = {}

@app.route("/callback")
def callback():
    auth_code = request.args.get("auth_code")
    state = request.args.get("state")
    if auth_code:
        auth_data["auth_code"] = auth_code
        return "Auth code received! You can close this tab."
    return "No auth code received."

def run_server():
    app.run(host="0.0.0.0", port=5000)

# Run the server in a background thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
