import logging
from http import HTTPStatus
from urllib.parse import urljoin

import requests

from strava import constants
from strava.exceptions import (
    ImproperlyConfigured,
    StravaError,
    Unauthenticated,
    PermissionDenied,
    NotFound,
    InvalidRequest,
    RequestLimitExceeded,
    PremiumAccountRequired,
)


logger = logging.getLogger('strava.client')


class RequestHandler:

    api_domain: str = 'www.strava.com'
    api_path: str = None
    access_token: str = None

    error_mapping = {
        HTTPStatus.BAD_REQUEST: InvalidRequest,
        HTTPStatus.UNAUTHORIZED: Unauthenticated,
        HTTPStatus.FORBIDDEN: PermissionDenied,
        HTTPStatus.NOT_FOUND: NotFound,
        HTTPStatus.PAYMENT_REQUIRED: PremiumAccountRequired,
        HTTPStatus.TOO_MANY_REQUESTS: RequestLimitExceeded,
    }

    def __init__(self):
        self.last_response = None
        self.fifteen_minute_rate = None
        self.fifteen_minute_rate_usage = None
        self.daily_rate = None
        self.daily_rate_usage = None

    def _build_url(self, path):
        if not self.api_path:
            raise ImproperlyConfigured("Missing the 'api_path' setting for the Strava Client.")

        domain = self.api_domain
        if not domain.startswith('http'):
            domain = f'https://{domain}'

        domain = domain if domain.endswith('/') else domain + '/'
        base_url = urljoin(domain, self.api_path.lstrip('/'))
        base_url = base_url if base_url.endswith('/') else base_url + '/'

        url = urljoin(base_url, path.lstrip('/'))
        return url.strip('/')

    def _dispatcher(self, method, path, files=None, body=None, **params):
        """
        :param method [str]: HTTP method.

        :param path [str]: URL path on the Strava API.

        :param params [Dict[str, Any]]: Dict of params to be passed as querystring on the request.

        :param files [Dict[str, IO]]: Dict of files to be uploaded to the Strava API.

        :param body [Dict[str, Any]]: request body.
        """
        url = self._build_url(path)
        context = {
            'http_method': method.upper(),
            'url': url,
            'params': params,
            'body': body,
        }

        self._before_request(context)

        kwargs = {'params': params}
        # just create arguments that exist.

        if self._get_authorization_header():
            kwargs['headers'] = self._get_authorization_header()
        if files:
            kwargs['files'] = files
        if body:
            kwargs['json'] = body

        response = requests.request(method.lower(), url, **kwargs)
        self._after_request(response)

        logger.info(
            "%s %s %d",
            method.upper(),
            response.request.url,
            response.status_code,
            extra=dict(request=response.request, response=response),
        )

        self.handle_response(response)
        self.last_response = response
        return response.json()

    def _get_authorization_header(self):
        if getattr(self, 'access_token', None):
            return {'authorization': 'Bearer {}'.format(self.access_token)}

    def _get_strava_limits(self, response):
        limits = response.headers.get(constants.RATE_LIMIT_HEADER)
        try:
            fifteen_minute_rate, daily_rate = limits.split(',')
            fifteen_minute_rate, daily_rate = int(fifteen_minute_rate), int(daily_rate)
        except Exception:
            logger.debug(f'invalid Strava rate limits header. Header {constants.RATE_LIMIT_HEADER} {limits}')
            fifteen_minute_rate, daily_rate = None, None

        usage = response.headers.get(constants.RATE_LIMIT_USAGE_HEADER)
        try:
            fifteen_minute_rate_usage, daily_rate_usage = usage.split(',')
            fifteen_minute_rate_usage, daily_rate_usage = int(fifteen_minute_rate_usage), int(daily_rate_usage)
        except Exception:
            logger.debug(f'invalid Strava rate limit usage header. Header {constants.RATE_LIMIT_USAGE_HEADER} {usage}')
            fifteen_minute_rate_usage, daily_rate_usage = None, None

        self.fifteen_minute_rate = fifteen_minute_rate
        self.fifteen_minute_rate_usage = fifteen_minute_rate_usage
        self.daily_rate = daily_rate
        self.daily_rate_usage = daily_rate_usage

    def _before_request(self, context):
        """
        Hook called before the request to be made

        :param context [Dict[str, Any]]: the context of the request.
        """
        if hasattr(self, '_before_request_subscribers'):
            for fn in self._before_request_subscribers:
                fn(context)

    def _after_request(self, response):
        """
        Hook called after the request to be made

        :param response requests.Response: the response object.
        """
        if hasattr(self, '_after_request_subscribers'):
            for fn in self._after_request_subscribers:
                fn(response)

    def before_request_hook(self, func):
        """
        Add a callable to be called before the request be made.

        callable signature: (context) where context is a dict
        containing the request data:
            - http_method,
            - url,
            - params,
            - body (request body),

        :param func [Callable]: callable to be called before make the request
        """
        assert callable(func), "'func' must be a callable"

        if not hasattr(self, '_before_request_subscribers'):
            self._before_request_subscribers = [func]
        else:
            self._before_request_subscribers.append(func)

    def after_request_hook(self, func):
        """
        Add a callable to be called before the request be made.

        callable signature: (respose) - The response object.

        :param func [Callable]: callable to be called before make the request
        """
        assert callable(func), "'func' must be a callable"

        if not hasattr(self, '_after_request_subscribers'):
            self._after_request_subscribers = [func]
        else:
            self._after_request_subscribers.append(func)

    @property
    def exceeded_fifteen_minutes_budget(self):
        """
        Indicates if the 15-minute requests budget was exceeded
        """
        if self.fifteen_minute_rate is not None and self.fifteen_minute_rate_usage is not None:
            return self.fifteen_minute_rate_usage >= self.fifteen_minute_rate

    @property
    def exceeded_daily_budget(self):
        """
        Indicates if the daily requests budget was exceeded
        """
        if self.daily_rate is not None and self.daily_rate_usage is not None:
            return self.daily_rate_usage >= self.daily_rate

    def handle_response(self, response):
        self._get_strava_limits(response)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            exp_cls = self.error_mapping.get(response.status_code, StravaError)
            raise exp_cls(response=response)
        return response
