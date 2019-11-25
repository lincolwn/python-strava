from django.conf import settings


DEFAULT_SETTINGS = {
    'CLIENT_ID': '',
    'CLIENT_SECRET': '',
    'REDIRECT_URI': '',
    'DEFAULT_ATHLETE_ID': None,
    'DEFAULT_REFRESH_TOKEN': None,
    'WEBHOOK_CALLBACK_URL': '',
    'WEBHOOK_VERIFY_TOKEN': 'STRAVA',
}


class StravaSettings:
    def __getattr__(self, key):
        if not getattr(settings, 'STRAVA'):
            raise AttributeError('Missing Strava configuration on django settings')
        strava = settings.STRAVA
        try:
            return strava.get(key, DEFAULT_SETTINGS[key])
        except KeyError:
            raise AttributeError


strava_settings = StravaSettings()
