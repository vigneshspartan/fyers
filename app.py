from flask import Flask, request

app = Flask(__name__)

@app.route("/callback")
def callback():
    auth_code = request.args.get("auth_code")
    state = request.args.get("state")
    return f"Hello World! Auth code: {auth_code}, State: {state}"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
