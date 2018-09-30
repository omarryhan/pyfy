import os
import sys
import webbrowser

from flask import Flask, redirect, abort, request, jsonify, url_for

from pyfy import Client, ClientCredentials, UserCredentials, AuthError
try:
    from spt_keys import KEYS
except:
    from spt_keys_template import KEYS

app = Flask(__name__)

client = Client()

@app.route('/authorize')
def authorize():
    export_keys()
    client.client_creds.load_from_env()
    if client.is_oauth_ready:
        return redirect(client.oauth_uri)
    else:
        return jsonify({'error_description': 'Client doesn\'nt have enough attributes to handle OAauth authorization flow authentication'}), 500


@app.route('/callback/spotify')  # You have to register this callback
def spotify_callback():
    if request.args.get('error'):
        return jsonify(dict(error=request.args.get('error_description')))
    elif request.args.get('code'):
        grant = request.args.get('code')
        state = request.args.get('state')
        try:
            user_creds = client.build_user_credentials(grant=grant, state=state, update_user_creds=True)  # Default is to update the client's user_creds object
        except AuthError as e:
            return jsonify(dict(error_description=e.msg)), e.code
        else:
            return jsonify(dict(user_creds=user_creds.__dict__, check_if_active=url_for('is_active', _external=True))), 200
    else:
        return abort(500)


@app.route('/is_active')
def is_active():
    return jsonify(
        dict(
            is_active=client.is_active,
            your_tracks=url_for('tracks', _external=True),
            your_playlists=url_for('playlists', _external=True)
        )
    )    


@app.route('/')
def index():
    return 'OK'


@app.route('/tracks')
def tracks():
    return jsonify(client.tracks)


@app.route('/playlists')
def playlists():
    return jsonify(client.playlists)
    

def export_keys():
    for k, v in KEYS.items():
        if v:
            os.environ[k] = v
            print("export " + k + "=" + v)


if __name__ == '__main__':
    webbrowser.open_new_tab('http://127.0.0.1:5000/authorize')
    app.run(host='127.0.0.1', port=5000, debug=True)
    #webapp = Thread(target=lambda: app.run(host='127.0.0.1', port=9872, debug=True))
    #webapp.start()
