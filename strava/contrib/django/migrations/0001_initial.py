# Generated by Django 2.2.6 on 2019-11-15 14:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StravaAuth',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token', models.CharField(max_length=50)),
                ('refresh_token', models.CharField(max_length=50)),
                ('athlete_id', models.PositiveIntegerField(db_index=True, unique=True)),
                ('expires_at', models.DateField(blank=True, null=True)),
                ('scope', models.CharField(blank=True, max_length=150, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='strava_auth', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
