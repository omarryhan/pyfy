import os
import webbrowser

from flask import Flask, redirect, abort, request, jsonify, url_for

from pyfy import Spotify, ClientCreds, UserCreds, AuthError

try:
    from spt_keys import KEYS
except:
    from spt_keys_template import KEYS

app = Flask(__name__)

spt = Spotify()
client = ClientCreds()
state = "123"


@app.route("/authorize")
def authorize():
    export_keys()
    client.load_from_env()
    spt.client_creds = client
    if spt.is_oauth_ready:
        return redirect(spt.auth_uri(state=state))
    else:
        return (
            jsonify(
                {
                    "error_description": "Client needs client_id, client_secret and a redirect uri in order to handle OAauth properly"
                }
            ),
            500,
        )


@app.route("/callback/spotify")  # You have to register this callback
def spotify_callback():
    if request.args.get("error"):
        return jsonify(dict(error=request.args.get("error_description")))
    elif request.args.get("code"):
        grant = request.args.get("code")
        callback_state = request.args.get("state")
        if callback_state != state:
            return abort(401)
        try:
            user_creds = spt.build_user_creds(grant=grant)
        except AuthError as e:
            return jsonify(dict(error_description=e.msg)), e.code
        else:
            return (
                jsonify(
                    dict(
                        user_creds=user_creds.__dict__,
                        check_if_active=url_for("is_active", _external=True),
                    )
                ),
                200,
            )
    else:
        return abort(500)


@app.route("/is_active")
def is_active():
    return jsonify(
        dict(
            is_active=spt.is_active,
            your_tracks=url_for("tracks", _external=True),
            your_playlists=url_for("playlists", _external=True),
        )
    )


@app.route("/dump_creds")
def dump_creds():
    # TODO: save both client and user creds and send to user as json files to downlaod
    return "Not Implemented"


@app.route("/")
def index():
    return "OK"


@app.route("/tracks")
def tracks():
    return jsonify(spt.user_tracks())


@app.route("/playlists")
def playlists():
    return jsonify(spt.user_playlists())


def export_keys():
    for k, v in KEYS.items():
        if v:
            os.environ[k] = v
            print("export " + k + "=" + v)


if __name__ == "__main__":
    webbrowser.open_new_tab("http://127.0.0.1:5000/authorize")
    app.run(host="127.0.0.1", port=5000, debug=True)
