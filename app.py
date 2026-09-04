import os
import secrets
import requests
from flask import Flask, redirect, request, session, jsonify

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "temporary-secret-key")

CLIENT_ID = os.environ.get("WITHINGS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("WITHINGS_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("WITHINGS_REDIRECT_URI")

AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"
TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
MEASURE_URL = "https://wbsapi.withings.net/measure"


@app.route("/")
def home():
    return """
    <h1>Withings API</h1>
    <p>Servidor funcionando correctamente.</p>
    <p><a href="/login">Conectar cuenta Withings</a></p>
    """


@app.route("/login")
def login():
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "scope": "user.info,user.metrics,user.activity",
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }

    req = requests.Request("GET", AUTHORIZE_URL, params=params).prepare()

    return redirect(req.url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return "No se recibió código de autorización.", 400

    if state != session.get("oauth_state"):
        return "Error de seguridad: state inválido.", 400

    token_data = {
        "action": "requesttoken",
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(TOKEN_URL, data=token_data)
    data = response.json()

    if data.get("status") != 0:
        return jsonify(data), 400

    body = data["body"]

    session["access_token"] = body["access_token"]
    session["refresh_token"] = body["refresh_token"]
    session["userid"] = body["userid"]

    return redirect("/measurements")


@app.route("/measurements")
def measurements():
    access_token = session.get("access_token")

    if not access_token:
        return redirect("/login")

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    payload = {
        "action": "getmeas",
        "category": 1
    }

    response = requests.post(
        MEASURE_URL,
        headers=headers,
        data=payload
    )

    return jsonify(response.json())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
