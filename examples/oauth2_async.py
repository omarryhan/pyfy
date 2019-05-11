import os
import aiofiles
import webbrowser
import json as stdlib_json

from sanic import Sanic, response
from sanic.exceptions import abort
from sanic.response import json

from pyfy import AsyncSpotify, ClientCreds, UserCreds, AuthError

try:
    from spt_keys import KEYS
except:
    from spt_keys_template import KEYS


app = Sanic(__name__)

local_address = "localhost"
local_port = "5000"
local_full_address = local_address + ":" + str(local_port)

spt = AsyncSpotify()
client = ClientCreds()
state = "123"


@app.route("/authorize")
def authorize(request):
    export_keys()
    client.load_from_env()
    spt.client_creds = client
    if spt.is_oauth_ready:
        return response.redirect(spt.auth_uri(state=state))
    else:
        return (
            json(
                {
                    "error_description": "Client needs client_id, client_secret and a redirect uri in order to handle OAauth properly"
                }
            ),
            500,
        )


@app.route("/callback/spotify")  # You have to register this callback
async def spotify_callback(request):
    if request.args.get("error"):
        return json(dict(error=request.args.get("error_description")))
    elif request.args.get("code"):
        grant = request.args.get("code")
        callback_state = request.args.get("state")
        if callback_state != state:
            abort(401)
        try:
            user_creds = await spt.build_user_creds(grant=grant)
            async with aiofiles.open(os.getcwd() + "SPOTIFY_CREDS.json", "w") as file:
                await file.write(stdlib_json.dumps(user_creds.__dict__))
        except AuthError as e:
            return json(dict(error_description=e.msg, error_code=e.code), e.code)
        else:
            await spt.populate_user_creds()
            print(os.getcwd())
            return await response.file(os.getcwd() + "SPOTIFY_CREDS.json")
            # return response.json(dict(user_creds=user_creds.__dict__, check_if_active=app.url_for('is_active', _scheme='http', _external=True, _server=local_full_address)), 200)
    else:
        return response.text("Something is wrong with your callback")


@app.route("/is_active")
async def is_active(request):
    return json(
        dict(
            is_active=await spt.is_active,
            your_tracks=app.url_for(
                "tracks", _scheme="http", _external=True, _server=local_full_address
            ),
            your_playlists=app.url_for(
                "playlists", _scheme="http", _external=True, _server=local_full_address
            ),
        )
    )


@app.route("/dump_creds")
def dump_creds(request):
    # TODO: save both client and user creds and send to user as json files to downlaod
    return response.text("Not Implemented")


@app.route("/")
def index(request):
    return response.text("OK")


@app.route("/tracks")
async def tracks(request):
    return json(await spt.user_tracks())


@app.route("/playlists")
async def playlists(request):
    return json(await spt.user_playlists())


def export_keys():
    for k, v in KEYS.items():
        if v:
            os.environ[k] = v
            print("export " + k + "=" + v)


if __name__ == "__main__":
    webbrowser.open_new_tab("http://" + local_full_address + "/authorize")
    app.run(host=local_address, port=str(local_port), debug=True)
