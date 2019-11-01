import logging
from functools import update_wrapper

import pytz
from django.db import models
from django.conf import settings
from django.utils import timezone

from strava.client import StravaApiClientV3
from strava.helpers import from_epoch_to_datetime
from strava.exceptions import Unauthenticated
from strava.contrib.django.settings import strava_settings


logger = logging.getLogger(__name__)


def ensure_auth(func):
    def wrapper(strava_auth, *args, **kwargs):
        if strava_auth.expires_at.astimezone(pytz.UTC) < timezone.now().astimezone(pytz.UTC):
            strava_auth.refresh_token()
        try:
            return func(strava_auth, *args, **kwargs)
        except Unauthenticated:
            strava_auth.refresh_token()
            return func(strava_auth, *args, **kwargs)
    return update_wrapper(wrapper, func)


class StravaAuth(models.Model):
    access_token = models.CharField(max_length=50)
    refresh_token = models.CharField(max_length=50)
    athlete_id = models.PositiveIntegerField(db_index=True)
    expires_at = models.DateField(null=True, blank=True)
    scope = models.CharField(max_length=150, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="strava_auth",
    )

    client_class = StravaApiClientV3

    @classmethod
    def from_user(cls, user):
        return cls.objects.get(user_id=user.id)

    @classmethod
    def from_athlete_id(cls, athlete_id):
        return cls.objects.get(athlete_id=athlete_id)

    @classmethod
    def authorization_url(cls, approval_prompt=None, scope=None, state=None, mobile=False):
        return cls.client_class.authorization_url(
            client_id=strava_settings.CLIENT_ID,
            redirect_uri=strava_settings.REDIRECT_URI,
            approval_prompt=approval_prompt,
            scope=scope,
            state=state,
            mobile=mobile
        )

    @property
    def client(self):
        if not hasattr(self, "_client"):
            self._client = self.client_class(access_token=self.access_token)
        return self._client

    def exchange_token(self, code, scope):
        auth_data = self.client.exchange_token(
            client_id=strava_settings.CLIENT_ID,
            client_secret=strava_settings.CLIENT_SECRET,
            code=code
        )

        auth_data["expires_at"] = from_epoch_to_datetime(auth_data["expires_at"])
        athlete = auth_data.pop("athlete")
        auth_data["athete_id"] = athlete["id"]
        auth_data["scope"] = scope

        if self.athlete_id and self.athlete_id != athlete["id"]:
            logger.warn("code exchanged of another user. A new StravaAuth will be created.")
            self._meta.model.create(**auth_data)

        fields_to_update = []
        for field, value in auth_data.items():
            if getattr(self, field) != value:
                setattr(self, field, value)
                fields_to_update.append(field)
        self.save(update_fields=fields_to_update)

    def refresh_token(self):
        auth_data = self.client.refresh_token(
            strava_settings.CLIENT_ID,
            strava_settings.CLIENT_SECRET,
            self.refresh_token
        )

        expires_at = from_epoch_to_datetime(auth_data["expires_at"])
        fields_to_update = ["access_token", "expires_at"]

        self.expires_at = expires_at
        self.access_token = auth_data["access_token"]
        if self.refresh_token != self.refresh_token:
            fields_to_update.append("refresh_token")
            self.refresh_token = auth_data["refresh_token"]
        self.save(update_fields=fields_to_update)

    def deauthorize(self):
        self.client.deauthorize(self.access_token)

    @ensure_auth
    def get_athlete_profile(self):
        return self.client.get_athlete_profile()

    @ensure_auth
    def get_activities(self, before=None, after=None, per_page=50, limit=None):
        return self.client.get_activities(before, after, per_page, limit)

    @ensure_auth
    def get_activity(self, activity_id, include_all_efforts=True):
        return self.client.get_activity(activity_id, include_all_efforts)

    @ensure_auth
    def explore_segments(self, bounds, activity_type=None, min_cat=None, max_cat=None):
        return self.client.explore_segments(bounds, activity_type, min_cat, max_cat)

    @ensure_auth
    def get_segment(self, segment_id):
        return self.client.get_segment(segment_id)

    @ensure_auth
    def get_segment_efforts(self, segment_id, per_page=50, limit=None):
        return self.client.get_segment_efforts(segment_id, per_page, limit)

    @ensure_auth
    def get_segment_effort(self, effort_id):
        return self.client.get_segment_effort(effort_id)
