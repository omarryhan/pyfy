export SPOTIFY_CLIENT_ID=PLACEHOLDER_CLIENT_ID;  # Create an app from [here](https://developer.spotify.com/dashboard/applications)
echo $SPOTIFY_CLIENT_ID;

export SPOTIFY_CLIENT_SECRET=PLACEHOLDER_CLIENT_SECRET;  # Create an app from [here](https://developer.spotify.com/dashboard/applications)
echo $SPOTIFY_CLIENT_SECRET;

export SPOTIFY_REDIRECT_URI=http://localhost:5000/callback/spotify;  # You have to register this call back in your Application's dashboard https://developer.spotify.com/dashboard/applications
echo $SPOTIFY_REDIRECT_URI;

export SPOTIFY_ACCESS_TOKEN=PLACEHOLDER_ACCESS_TOKEN;  # Get a Spotify token from [here](https://beta.developer.spotify.com/console/get-current-user/)  ****Check all scopes**
echo $SPOTIFY_ACCESS_TOKEN;

export PYFY_TEST_INTEGRATION_SYNC=true;  # set to true for sync integration testing
echo $PYFY_TEST_INTEGRATION_SYNC;

export PYFY_TEST_INTEGRATION_ASYNC=true;  # set to true for async integration testing
echo $PYFY_TEST_INTEGRATION_ASYNC;