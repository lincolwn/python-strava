from functools import partial
from urllib.parse import urlunsplit, urlencode

from strava.base import RequestHandler
from strava.constants import APPROVAL_PROMPT, SCOPE, DEFAULT_VERIFY_TOKEN
from strava.helpers import BatchIterator, from_datetime_to_epoch


class StravaApiClientV3(RequestHandler):
    api_path = 'api/v3/'

    def __init__(self, access_token=None):
        self.access_token = access_token

    @classmethod
    def authorization_url(
        cls,
        client_id,
        redirect_uri,
        approval_prompt=None,
        scope=None,
        state=None,
        mobile=False,
        deep_link=False,
    ):
        """
        Returns the Strava authorization URL.

        See docs: https://developers.strava.com/docs/authentication/

        :param client_id [str]: Strava Client ID.
        :param redirect_uri [str]: URI that the user will be redirected after authetication.
        :param approval_prompt [str]: indicates if Strava should show the autorization prompt to the user
        :param scope [Sequence[str]]: list/tuple of the requested scope.
        :params state [str]: A value to be returned in the redirect URI.
        :param mobile [bool]: Returns mobile link version.
        :param deep_link [bool]: Returns ios deep link version.
        """

        oauth_path = 'oauth/authorize/'
        mobile_oauth_path = 'oauth/mobile/authorize/'

        approval_prompt = approval_prompt or APPROVAL_PROMPT.AUTO
        assert approval_prompt in APPROVAL_PROMPT, (
            "Invalid value for 'approval_prompt': '{}'".format(approval_prompt),
            "Valid values are: {}".format([items for items in APPROVAL_PROMPT.values()])
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
            'response_type': 'code',
            'approval_prompt': approval_prompt,
            'scope': ','.join(scope)
        }

        if state:
            assert isinstance(state, str), "Invalid value for 'state'. This value must be str."
            qs['state'] = state

        scheme = 'https'
        path = oauth_path
        if mobile and not deep_link:
            path = mobile_oauth_path
        elif deep_link:
            scheme = 'strava'
            path = f'//{mobile_oauth_path}'

        return urlunsplit((scheme, cls.api_domain, path, urlencode(qs), ''))

    def subscribe_webhook(self, client_id, client_secret, callback_url, verify_token=DEFAULT_VERIFY_TOKEN):
        path = 'push_subscriptions/'

        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'callback_url': callback_url,
            'verify_token': verify_token
        }
        return self._dispatcher('post', path, is_webhook=True, **params)

    def validate_webhook_subscription(self, hub_mode, hub_challenge, verify_token=None):
        assert hub_mode == 'subscribe', "Invalid 'hub_mode'."

        if verify_token:
            assert verify_token == DEFAULT_VERIFY_TOKEN, "Invalid 'verify token'."
        return {"hub.challenge": hub_challenge}

    def check_webhook_subscription(self, client_id, client_secret):
        path = 'push_subscriptions/'

        params = {'client_id': client_id, 'client_secret': client_secret}
        return self._dispatcher('get', path, is_webhook=True, **params)

    def delete_webhook_subscription(self, subscription_id, client_id, client_secret):
        path = 'push_subscriptions/'

        params = {'id': subscription_id, 'client_id': client_id, 'client_secret': client_secret}
        return self._dispatcher('delete', path, is_webhook=True, **params)

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

    def deauthorize(self, access_token):
        """
        Deauthorize the application.

        See docs: https://developers.strava.com/docs/authentication/
        """

        path = 'oauth/deauthorize/'
        self._dispatcher('post', path, access_token=access_token)

    def get_athlete_profile(self):
        """
        Return the profile of the authenticated user (access_token owner).

        See docs: http://developers.strava.com/docs/reference/#api-Athletes-getLoggedInAthlete
        """

        path = 'athlete/'
        return self._dispatcher('get', path)

    def get_activities(self, before=None, after=None, per_page=50, limit=None):
        """
        Get the athele activities

        See docs: http://developers.strava.com/docs/reference/#api-Activities-getLoggedInAthleteActivities

        :param before [datetime]: datetime to use for filtering activities that have taken place before a certain time
        :param after [datetime]: datetime to use for filtering activities that have taken place after a certain time
        :param per_page [int]: page size
        :param limit [int]: maximum number of activities to fetch

        Note: 'before' and 'after' will be considered in UTC.
        """

        path = 'athlete/activities/'

        params = {}
        if before:
            params['before'] = from_datetime_to_epoch(before)
        if after:
            params['after'] - from_datetime_to_epoch(after)

        fetcher = partial(self._dispatcher, 'get', path, **params)
        return BatchIterator(fetcher, per_page=per_page, limit=limit)

    def get_activity(self, activity_id, include_all_efforts=True):
        """
        Get an athlete activity by id

        See docs: http://developers.strava.com/docs/reference/#api-Activities-getActivityById

        :param activity_id [int]: activity's id
        :param include_all_efforts [bool]: include segment efforts in the response
        """

        path = f'activities/{activity_id}/'
        return self._dispatcher('get', path, include_all_efforts=include_all_efforts)

    def explore_segments(self, bounds, activity_type=None, min_cat=None, max_cat=None):
        """
        Returns the top 10 segments matching a specified query.

        See docs: http://developers.strava.com/docs/reference/#api-Segments-exploreSegments

        :param bounds [Sequence[float]]:  The latitude and longitude for two points describing a rectangular
            boundary for the search: [southwest corner latitutde, southwest corner longitude, northeast corner
            latitude, northeast corner longitude]. Bounds should be a sequence of points sequence:
            Example: [[lat, long], [lat, long]]

        :param activity_type [str]: Desired activity type. Can be 'running' or 'riding'.
        :param min_cat [int]: the minimum climbing category.
        :param max_cat [int]: the maximum climbing category.

        """

        path = 'segments/explore/'

        assert len(bounds) == 4, (
            "Invalid bounds. Must be '[southwest_corner_latitude, southwest_corner_longitude, "
            "northeast_corner_latitude, northeast_corner_longitude]'"
        )
        params = {'bounds': ','.join(str(bound) for bound in bounds)}
        if activity_type:
            assert activity_type in ('running', 'riding'), "Invalid 'activity_type'. Must be 'running' or 'riding'"
            params['activity_type'] = activity_type
        if min_cat:
            params['min_cat'] = min_cat
        if max_cat:
            params['max_cat'] = max_cat

        return self._dispatcher('get', path, **params)

    def get_segment(self, segment_id):
        """
        Return the specified segment by id.

        See docs: http://developers.strava.com/docs/reference/#api-Segments-getSegmentById

        :param segment_id [int]: Segment id.
        """

        path = f'segments/{segment_id}/'
        return self._dispatcher('get', path)

    def get_segment_efforts(self, segment_id, per_page=50, limit=None):
        """
        Return all segment's efforts from activities of the authenticated user.

        See docs: http://developers.strava.com/docs/reference/#api-SegmentEfforts-getEffortsBySegmentId

        :param segment_id [int]: Segment id.
        :param per_page [int]: page size.
        :param limit [int]: maximum number of activities to fetch.
        """

        path = f'segments/{segment_id}/all_efforts/'
        fetcher = partial(self._dispatcher, 'get', path)
        return BatchIterator(fetcher, per_page=per_page, limit=limit)

    def get_segment_effort(self, effort_id):
        """
        Returns a segment effort from an activity that is owned by the authenticated athlete.

        See docs: http://developers.strava.com/docs/reference/#api-SegmentEfforts-getSegmentEffortById

        :param effort_id [id]: segment effort id
        """

        path = f'segment_efforts/{effort_id}/'
        return self._dispatcher('get', path)
