from django.conf import settings


class StravaSettings:
    def __getattr__(self, key):
        if not getattr(settings, "STRAVA"):
            raise AttributeError("Missing Strava configuration on django settings")
        strava = settings.STRAVA
        try:
            return strava[key]
        except KeyError:
            raise AttributeError


strava_settings = StravaSettings()
