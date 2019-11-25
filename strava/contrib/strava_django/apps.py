from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StravaAuthConfig(AppConfig):
    name = "strava.contrib.strava_django"
    verbose_name = _("Strava Auth")

    def ready(self):
        pass
