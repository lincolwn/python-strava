import json
import logging
from http import HTTPStatus
from urllib.parse import urljoin

import requests

from strava.exception import (
    ImproperlyConfigured,
    StravaError,
    Unauthenticated,
    PermissionDenied,
    NotFound,
)


logger = logging.getLogger('strava.client')


class RequestHandler:

    api_domain: str = 'www.strava.com'
    webhook_domain: str = 'api.strava.com'
    api_path: str = None
    access_token: str = None

    def _build_url(self, path, is_webhook=False):
        if not self.api_path:
            raise ImproperlyConfigured("Missing the 'api_path' setting for the Strava Client.")

        domain = self.api_domain if not is_webhook else self.webhook_domain
        if not domain.startswith('http'):
            domain = f'https://{domain}'

        domain = domain if domain.endswith('/') else domain + '/'
        base_url = urljoin(domain, self.api_path.lstrip('/'))
        base_url = base_url if base_url.endswith('/') else base_url + '/'

        url = urljoin(base_url, path.lstrip('/'))
        return url

    def _dispatcher(self, method, path, files=None, body=None, is_webhook=False, **params):
        """
        :param path [str]: URL path on the Strava API.

        :param method [str]: HTTP method.

        :param params [Dict[str, Any]]: Dict of params to be passed as querystring on the request.

        :param files [Dict[str, IO]]: Dict of files to be uploaded to the Strava API.

        :param body [Dict[str, Any]]: request body.
        """
        url = self._build_url(path, is_webhook)
        context = {
            'http_method': method.upper(),
            'url': url,
            'params': params,
            'body': body,
            'is_webhook': is_webhook
        }

        self._before_request(context)

        kwargs = {'headers': self._get_authorization_header()}
        # just create arguments that exist.
        if params:
            kwargs['params'].update(params)
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

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = None
        return response_data

    def _get_authorization_header(self):
        return {'authorization': 'Bearer {}'.format(self.get_access_token())}

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
            for fn in self._before_request_subscribers:
                fn(response)

    def get_access_token(self):
        assert self.access_token, "You must provide an access token."
        return self.access_token

    def before_request_hook(self, func):
        """
        Add a callable to be called before the request be made.

        callable signature: (context) where context is a dict
        containing the request data:
            - http_method,
            - url,
            - params,
            - body (request body),
            - is_webhook

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

    def handle_response(self, response):
        exc_class = None
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            exc_class = Unauthenticated
        elif response.status_code == HTTPStatus.FORBIDDEN:
            exc_class = PermissionDenied
        elif response.status_code == HTTPStatus.NOT_FOUND:
            exc_class = NotFound
        elif response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
            exc_class = StravaError

        if exc_class:
            raise exc_class(response=response)
        return response
