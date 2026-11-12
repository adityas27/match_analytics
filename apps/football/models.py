from typing import ClassVar

from django.db import models


class Competition(models.Model):
    external_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    country_name = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=32, blank=True)
    international = models.BooleanField(null=True)
    youth = models.BooleanField(null=True)
    raw_data = models.JSONField(default=dict)

    def __str__(self) -> str:
        return f"{self.name} ({self.external_id})"

class Season(models.Model):
    external_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict)
    def __str__(self) -> str:
        return f"{self.name} ({self.external_id})"

class Team(models.Model):
    external_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=32, blank=True)
    country_name = models.CharField(max_length=255, blank=True)
    raw_data = models.JSONField(default=dict)
    def __str__(self) -> str:
        return f"{self.name} ({self.external_id})"

class Player(models.Model):
    external_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    nickname = models.CharField(max_length=255, blank=True)
    country_name = models.CharField(max_length=255, blank=True)
    raw_data = models.JSONField(default=dict)
    def __str__(self) -> str:
        return f"{self.name} ({self.external_id})"

class Match(models.Model):
    external_id = models.PositiveIntegerField(unique=True)
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT)
    season = models.ForeignKey(Season, on_delete=models.PROTECT)
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="home_matches")
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="away_matches")
    match_date = models.DateField(null=True)
    kick_off = models.TimeField(null=True)
    home_score = models.IntegerField(null=True)
    away_score = models.IntegerField(null=True)
    match_status = models.CharField(max_length=64, blank=True)
    match_status_360 = models.CharField(max_length=64, blank=True)
    match_week = models.PositiveIntegerField(null=True)
    raw_data = models.JSONField(default=dict)
    source_path = models.CharField(max_length=1024, blank=True)
    def __str__(self) -> str:
        return f"{self.home_team.name} vs {self.away_team.name} ({self.external_id})"

class MatchPlayer(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    player = models.ForeignKey(Player, on_delete=models.PROTECT)
    jersey_number = models.PositiveIntegerField(null=True)
    cards = models.JSONField(default=list)
    positions = models.JSONField(default=list)
    raw_data = models.JSONField(default=dict)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=("match", "team", "player"), name="unique_match_team_player")
        ]


class MatchEvent(models.Model):
    external_id = models.UUIDField(unique=True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="events")
    event_index = models.PositiveIntegerField()
    period = models.PositiveSmallIntegerField(null=True)
    timestamp = models.TimeField(null=True)
    minute = models.PositiveIntegerField(null=True)
    second = models.PositiveSmallIntegerField(null=True)
    event_type_id = models.PositiveIntegerField(null=True)
    event_type_name = models.CharField(max_length=128)
    team = models.ForeignKey(Team, null=True, on_delete=models.PROTECT)
    player = models.ForeignKey(Player, null=True, on_delete=models.PROTECT)
    possession = models.PositiveIntegerField(null=True)
    possession_team_id = models.PositiveIntegerField(null=True)
    location = models.JSONField(null=True)
    payload = models.JSONField(default=dict)
    raw_data = models.JSONField(default=dict)

    class Meta:
        ordering = ("match", "event_index")


class Match360Frame(models.Model):
    event_uuid = models.UUIDField(unique=True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="frames")
    visible_area = models.JSONField(default=list)
    freeze_frame = models.JSONField(default=list)
    raw_data = models.JSONField(default=dict)


class IngestionRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"
        DRY_RUN = "dry_run"

    operation = models.CharField(max_length=64)
    dataset = models.CharField(max_length=64)
    source_path = models.CharField(max_length=1024)
    status = models.CharField(max_length=16, choices=Status.choices)
    checkpoint = models.CharField(max_length=1024, blank=True)
    files_seen = models.PositiveIntegerField(default=0)
    records_seen = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_skipped = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
