import os
import webbrowser

from sanic import Sanic, response
from sanic.response import json, text
from sanic.exceptions import abort

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
        except AuthError as e:
            return json(dict(error_description=e.msg, error_code=e.code), e.code)
        else:
            await spt.populate_user_creds()
            user_creds.save_as_json()
            return response.text(
                "Your user credentials where successfully saved, you can now easily access them in any script by simply calling: user_creds.load_from_json()"
            )
    else:
        return response.text("Something is wrong with your callback")


def export_keys():
    for k, v in KEYS.items():
        if v:
            os.environ[k] = v
            print("export " + k + "=" + v)


if __name__ == "__main__":
    webbrowser.open_new_tab("http://" + local_full_address + "/authorize")
    app.run(host=local_address, port=str(local_port), debug=True)
