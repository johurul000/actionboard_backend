# Generated by Django 4.2.8 on 2025-05-30 01:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0002_zoomprofile'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('meetings', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='meeting',
            options={'ordering': ['-start_time']},
        ),
        migrations.RenameField(
            model_name='meeting',
            old_name='external_meeting_id',
            new_name='meeting_id',
        ),
        migrations.RenameField(
            model_name='meeting',
            old_name='date',
            new_name='start_time',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='title',
        ),
        migrations.AddField(
            model_name='meeting',
            name='duration',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='meeting',
            name='end_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='meeting',
            name='host',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hosted_meetings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='meeting',
            name='recording_ready',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='meeting',
            name='topic',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='meeting',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='meeting',
            name='zoom_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='meetings', to='integrations.zoomprofile'),
        ),
        migrations.AlterField(
            model_name='meeting',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('ended', 'Ended'), ('deleted', 'Deleted')], default='active', max_length=20),
        ),
    ]
