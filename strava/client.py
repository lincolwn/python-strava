from urllib.parse import urlunsplit, urlencode

from strava.base import RequestHandler
from strava.constant import APPROVAL_PROMPT, SCOPE


class ClientApiV3(RequestHandler):
    api_path = 'api/v3/'

    def __init__(self, access_token=None):
        self.access_token = access_token

    def authorization_url(self, client_id, redirect_uri, approval_prompt=None, scope=None, state=None, mobile=False):
        """
        Returns the Strava authorization URL.

        See docs: https://developers.strava.com/docs/authentication/

        :param client_id [str]: Strava Client ID.
        :param redirect_uri [str]: URI that the user will be redirected after authetication.
        :param approval_prompt [str]: indicates if Strava should show the autorization prompt to the user
        :param scope [Sequence[str]]: list/tuple of the requested scope.
        :params state [str]: A value to be returned in the redirect URI.
        :param mobile [bool]: Indicates if the user should be redirect to the mobile page or not.
        """

        oauth_path = 'oauth/authorize/'
        mobile_oauth_path = 'oauth/mobile/authorize/'

        approval_prompt = approval_prompt or APPROVAL_PROMPT.AUTO
        assert approval_prompt in APPROVAL_PROMPT, (
            "Invalid value for 'approval_prompt': '{}'".format(approval_prompt),
            "Valid values are: {}".format(APPROVAL_PROMPT.values())
        )

        scope = scope or [SCOPE.READ, SCOPE.ACTIVITY_READ_ALL]

        invalid_scope = set(scope) - set(SCOPE.values())

        assert not invalid_scope, (
            "Invalid value for 'scope': {}".format(invalid_scope),
            "Valid values are: {}".format(SCOPE.values())
        )

        qs = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'approval_prompt': approval_prompt,
            'scope': ','.join(scope)
        }

        if state:
            assert isinstance(state, str), "Invalid value for 'state'. This value must be str."
            qs['state'] = state

        path = mobile_oauth_path if mobile else oauth_path

        return urlunsplit(('https', self.api_domain, path, urlencode(qs), ''))

    def exchange_token(self, client_id, client_secret, code):
        """
        Exchange the authorization code (received from Strava) for the token.

        See docs: https://developers.strava.com/docs/authentication/

        :param client_id [str]: Strava Client ID
        :param client_secret [str]: Strava Client Secret
        :param code [str]: Temporary authorization code received by Strava.
        """

        path = 'oauth/token/'

        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }

        data = self._dispatcher('post', path, **params)

        self.access_token = data['access_token']
        return data

    def refresh_token(self, client_id, client_secret, refresh_token):
        """
        Get the new access token and refresh token from Strava given a refresh token.

        See docs: https://developers.strava.com/docs/authentication/

        :param client_id [str]: Strava Client ID
        :param client_secret [str]: Strava Client Secret
        :param refresh_token [str]: Refresh token received by Strava.
        """

        path = 'oauth/token/'

        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        data = self._dispatcher('post', path, **params)

        self.access_token = data['access_token']
        return data

    def deauthorize(self):
        """
        Deauthorize the application.

        See docs: https://developers.strava.com/docs/authentication/
        """

        path = 'oauth/deauthorize/'

        self._dispatcher('post', path)
