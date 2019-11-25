from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class StravaAuth(models.Model):
    access_token = models.CharField(max_length=50, null=True, blank=True)
    refresh_token = models.CharField(max_length=50, null=True, blank=True)
    athlete_id = models.PositiveIntegerField(db_index=True, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scope = models.CharField(max_length=150, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="strava_auth",
    )

    def bind_user(self, user):
        user_model = get_user_model()
        assert isinstance(user, user_model), f"User argument must be {settings.AUTH_USER_MODEL}"

        if self._meta.model.objects.filter(user_id=user.pk).exclude(id=self.id):
            raise ValidationError("User is already in use.")

        self.user_id = user.pk
        self.save(update_fields=["user_id"])
