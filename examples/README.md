# Examples

## 1. OAUTH2 (Requires Flask)

### Requiremetns:

1. Copy `spt_keys_template.py` to a new file and name it `spt_key.py`
2. Fillout the newly created file with your credentials
3. Register your callbacks here: https://developer.spotify.com/dashboard/applications/
4. Download any browser extension that pretty prints JSON data. [e.g.](https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc?hl=en) 
  
### Asuming you git cloned the project and you're in its root dir, run:

    $pip install pyfy flask && python examples/oauth2.py

- The example will guide you through Spotify's OAuth2 authorization code flow and show you your user credentials

## 2. OAUTH2 async (Requires Sanic)

### Requirements:

1. Copy `spt_keys_template.py` to a new file and name it `spt_key.py`
2. Fillout the newly created file with your credentials
3. Register your callbacks here: https://developer.spotify.com/dashboard/applications/
4. Download any browser extension that pretty prints JSON data. [e.g.](https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc?hl=en) 

    $pip install pyfy sanic && python examples/oauth2_async.py

- The example will guide you through Spotify's OAuth2 authorization code flow and show you your user credentials