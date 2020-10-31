class ImproperlyConfigured(Exception):
    pass


class StravaError(Exception):
    default_message = 'Unknown Error.'

    def __init__(self, message=None, response=None, *args, **kwargs):
        self.message = message or self.default_message
        self.response = response
        super().__init__(self.message, *args, **kwargs)


class Unauthenticated(StravaError):
    default_message = 'You are not authenticated.'


class PermissionDenied(StravaError):
    default_message = 'You do not have permission to perform this action.'


class NotFound(StravaError):
    default_message = 'Resource not found.'


class InvalidRequest(StravaError):
    default_message = 'Validation error.'


class RequestLimitExceeded(StravaError):
    default_message = 'Limit of requests for the period was exceeded.'

    def __init__(self, message=None, response=None, exceeded_period=None, *args, **kwargs):
        self.exceeded_period = exceeded_period
        super().__init__(message, response, exceeded_period, *args, **kwargs)


class PremiumAccountRequired(StravaError):
    default_message = 'Premium account required for this operation.'
