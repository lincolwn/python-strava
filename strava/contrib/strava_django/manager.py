import logging
from functools import update_wrapper

import pytz
from django.utils import timezone
from django.core.exceptions import ValidationError

from strava.client import StravaApiClientV3
from strava.helpers import from_epoch_to_datetime
from strava.exceptions import Unauthenticated
from strava.contrib.strava_django.models import StravaAuth
from strava.contrib.strava_django.settings import strava_settings


logger = logging.getLogger(__name__)


def ensure_auth(func):
    def wrapper(strava_manager, *args, **kwargs):
        strava_auth = strava_manager.auth_instance
        expires_at = strava_auth.expires_at
        if expires_at is not None and expires_at.astimezone(pytz.UTC) < timezone.now().astimezone(pytz.UTC):
            strava_manager.refresh_token()
        try:
            return func(strava_manager, *args, **kwargs)
        except Unauthenticated:
            strava_manager.refresh_token()
            return func(strava_manager, *args, **kwargs)
    return update_wrapper(wrapper, func)


class StravaManager:
    auth_model = StravaAuth
    client_class = StravaApiClientV3

    def __init__(self, user=None, athlete_id=None):
        self.user = user
        self.athlete_id = athlete_id

    @classmethod
    def for_user(cls, user):
        return cls(user=user)

    @classmethod
    def by_athlete_id(cls, athlete_id):
        return cls(athlete_id=athlete_id)

    @classmethod
    def by_default_athlete(cls):
        auth_model = cls().get_auth_model()
        auth_model.objects.get_or_create(
            athlete_id=strava_settings.DEFAULT_ATHLETE_ID,
            defaults=dict(
                refresh_token=strava_settings.DEFAULT_REFRESH_TOKEN,
            )
        )
        return cls.by_athlete_id(strava_settings.DEFAULT_ATHLETE_ID)

    @classmethod
    def authorization_url(cls, approval_prompt=None, scope=None, state=None, mobile=False):
        return cls().get_client_class().authorization_url(
            client_id=strava_settings.CLIENT_ID,
            redirect_uri=strava_settings.REDIRECT_URI,
            approval_prompt=approval_prompt,
            scope=scope,
            state=state,
            mobile=mobile
        )

    @classmethod
    def exchange_token(cls, code, scope):
        auth_data = cls().get_client().exchange_token(
            client_id=strava_settings.CLIENT_ID,
            client_secret=strava_settings.CLIENT_SECRET,
            code=code
        )

        auth_data["expires_at"] = from_epoch_to_datetime(auth_data["expires_at"])
        athlete = auth_data.pop("athlete")
        auth_data["athete_id"] = athlete["id"]
        auth_data["scope"] = scope

        auth_model = cls().get_auth_model()
        try:
            auth_instance = auth_model.objects.get(athelte_id=auth_data["athlete_id"])
        except auth_model.DoesNotExist:
            auth_instance = auth_model.objects.create(**auth_data)
        else:
            fields_to_update = []
            for field, value in auth_data.items():
                if getattr(auth_instance, field) != value:
                    setattr(auth_instance, field, value)
                    fields_to_update.append(field)
            auth_instance.save(update_fields=fields_to_update)
        return cls.by_athlete_id(auth_instance.athlete_id)

    @property
    def auth_instance(self):
        if getattr(self, "_auth_instance", None):
            return self._auth_instance

        lkp, self._auth_instance = {}, None
        if self.user:
            lkp["user_id"] = self.user.pk
        if self.athlete_id:
            lkp["athlete_id"] = self.athlete_id

        if lkp:
            try:
                self._auth_instance = self.get_auth_model().objects.get(**lkp)
            except self.get_auth_model().DoesNotExist:
                return
        return self._auth_instance

    def bind_user(self, user):
        self.auth_instance.bind_user(user)
        self.user = user

    def get_auth_model(self):
        assert self.auth_model is not None, "You must set the auth_model attribute"
        return self.auth_model

    def get_client_class(self):
        assert self.client_class is not None, "You must set the client_class attribute"
        return self.client_class

    def get_client(self):
        access_token = getattr(self.auth_instance, "access_token", None)
        return self.get_client_class()(access_token=access_token)

    def refresh_token(self):
        auth_data = self.get_client().refresh_token(
            strava_settings.CLIENT_ID,
            strava_settings.CLIENT_SECRET,
            self.auth_instance.refresh_token
        )

        expires_at = from_epoch_to_datetime(auth_data["expires_at"])
        fields_to_update = ["access_token", "expires_at"]

        self.auth_instance.expires_at = expires_at
        self.auth_instance.access_token = auth_data["access_token"]
        if self.auth_instance.refresh_token != self.auth_instance.refresh_token:
            fields_to_update.append("refresh_token")
            self.auth_instance.refresh_token = auth_data["refresh_token"]
        self.auth_instance.save(update_fields=fields_to_update)

    def deauthorize(self):
        self.get_client().deauthorize(self.access_token)

    @ensure_auth
    def get_athlete_profile(self):
        return self.get_client().get_athlete_profile()

    @ensure_auth
    def get_activities(self, before=None, after=None, per_page=50, limit=None):
        return self.get_client().get_activities(before, after, per_page, limit)

    @ensure_auth
    def get_activity(self, activity_id, include_all_efforts=True):
        return self.get_client().get_activity(activity_id, include_all_efforts)

    @ensure_auth
    def explore_segments(self, bounds, activity_type=None, min_cat=None, max_cat=None):
        return self.get_client().explore_segments(bounds, activity_type, min_cat, max_cat)

    @ensure_auth
    def get_segment(self, segment_id):
        return self.get_client().get_segment(segment_id)

    @ensure_auth
    def get_segment_efforts(self, segment_id, per_page=50, limit=None):
        return self.get_client().get_segment_efforts(segment_id, per_page, limit)

    @ensure_auth
    def get_segment_effort(self, effort_id):
        return self.get_client().get_segment_effort(effort_id)

    def subscribe_webhook(self):
        return self.get_client().subscribe_webhook(
            client_id=strava_settings.CLIENT_ID,
            client_secret=strava_settings.CLIENT_SECRET,
            callback_url=strava_settings.WEBHOOK_CALLBACK_URL,
            verify_token=strava_settings.WEBHOOK_VERIFY_TOKEN,
        )

    def validate_webhook_subscription(self, hub_mode, hub_challenge, verify_token):
        if verify_token != strava_settings.WEBHOOK_VERIFY_TOKEN:
            raise ValidationError({"verify_token": f"Invalid verify_token parameter: '{verify_token}'"})
        return self.get_client().validate_webhook_subscription(hub_mode, hub_challenge)

    def check_webhook_subscription(self):
        return self.get_client().check_webhook_subscription(strava_settings.CLIENT_ID, strava_settings.CLIENT_SECRET)

    def delete_webhook_subscription(self, subscription_id):
        return self.get_client().delete_webhook_subscription(
            subscription_id=subscription_id,
            client_id=strava_settings.CLIENT_ID,
            client_secret=strava_settings.CLIENT_SECRET,
        )
