# Examples

## 1. OAUTH2 (Requires flask)

### Requiremetns:

1. Copy `spt_keys_template.py` to a new file and name it `spt_key.py`
2. Fillout the newly created file with your credentials
3. Download any browser extension that pretty prints JSON data. [e.g.](https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc?hl=en) 
  
### Asuming you git cloned the project and you're in its root dir, run:

    $pip install pyfy flask && python examples/oauth.py

- The example will guide you through Spotify's OAuth2 authorization code flow and let you download your credentials as a json file
