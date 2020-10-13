class Enum:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, value):
        return value in self.__dict__.values()

    def __iter__(self):
        return iter(self.__dict__.values())

    def values(self):
        return iter(self.__dict__.values())


APPROVAL_PROMPT = Enum(
    AUTO='auto',
    FORCE='force',
)


SCOPE = Enum(
    READ='read',
    READ_ALL='read_all',
    PROFILE_READ_ALL='profile:read_all',
    PROFILE_WRITE='profile:write',
    ACTIVITY_READ='activity:read',
    ACTIVITY_READ_ALL='activity:read_all',
    ACTIVITY_WRITE='activity:write',
)


DEFAULT_VERIFY_TOKEN = 'STRAVA'

STRAVA_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

RATE_LIMIT_HEADER = 'X-RateLimit-Limit'

RATE_LIMIT_USAGE_HEADER = 'X-RateLimit-Usage'
