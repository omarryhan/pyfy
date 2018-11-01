# Examples

## 1. oauth2.py (Requires Flask)

### Goal

- Demonstrate how a client should perform oauth2 authorization code flow.
- Show some user resources

### Requirements and steps:

1. Copy `spt_keys_template.py` to a new file and name it `spt_key.py`
2. Fillout the newly created file with your credentials (Only Client secret and Client Id are required for this example. You can leave the rest empty)
3. Register your callbacks here: https://developer.spotify.com/dashboard/applications/
4. Download any browser extension that pretty prints JSON data. [e.g.](https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc?hl=en) 
  
### Asuming you git cloned the project and you're in its root dir, run:

    $pip install pyfy flask && python examples/oauth2.py


## 2. oauth2_async.py (Requires Sanic)

### Goal

- Demonstrate how a client should perform oauth2 authorization code flow asynchronously.
- Show some user resources

### Requirements and steps:

1. Copy `spt_keys_template.py` to a new file and name it `spt_key.py`
2. Fillout the newly created file with your credentials (Only Client secret and Client Id are required for this example. You can leave the rest empty)
3. Register your callbacks here: https://developer.spotify.com/dashboard/applications/
4. Download any browser extension that pretty prints JSON data. [e.g.](https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc?hl=en) 

    $pip install pyfy sanic && python examples/oauth2_async.py


## 3. save_user_creds.py (Requires Sanic)

### Goal

- Save your user credentials to disk after perfoming Oauth2 authorization code flow to make it easier accessing your user credentials afterwards.

### Requirements and steps:

1. Copy `spt_keys_template.py` to a new file and name it `spt_key.py`
2. Fillout the newly created file with your credentials (Only Client secret and Client Id are required for this example. You can leave the rest empty)
3. Register your callbacks here: https://developer.spotify.com/dashboard/applications/
4. Download any browser extension that pretty prints JSON data. [e.g.](https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc?hl=en) 

    $pip install pyfy sanic && python examples/save_user_creds.py

