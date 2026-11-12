from django.contrib import admin

from .models import (
    Competition,
    IngestionRun,
    Match,
    Match360Frame,
    MatchEvent,
    MatchPlayer,
    Player,
    Season,
    Team,
)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "external_id", "country_name", "gender", "international", "youth")
    list_filter = ("country_name", "gender", "international", "youth")
    search_fields = ("name", "external_id", "country_name")
    ordering = ("name",)


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "external_id")
    search_fields = ("name", "external_id")
    ordering = ("-external_id", "name")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "external_id", "country_name", "gender")
    list_filter = ("country_name", "gender")
    search_fields = ("name", "external_id", "country_name")
    ordering = ("name",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "nickname", "external_id", "country_name")
    list_filter = ("country_name",)
    search_fields = ("name", "nickname", "external_id", "country_name")
    ordering = ("name",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "match_date",
        "kick_off",
        "home_team",
        "away_team",
        "competition",
        "season",
        "home_score",
        "away_score",
        "match_status",
    )
    list_filter = ("competition", "season", "match_status", "match_status_360", "match_date")
    search_fields = (
        "external_id",
        "competition__name",
        "season__name",
        "home_team__name",
        "away_team__name",
        "match_status",
    )
    ordering = ("-match_date", "kick_off", "external_id")
    date_hierarchy = "match_date"
    autocomplete_fields = ("competition", "season", "home_team", "away_team")


@admin.register(MatchPlayer)
class MatchPlayerAdmin(admin.ModelAdmin):
    list_display = ("match", "team", "player", "jersey_number")
    list_filter = ("team", "match")
    search_fields = (
        "match__external_id",
        "match__home_team__name",
        "match__away_team__name",
        "team__name",
        "player__name",
        "player__nickname",
    )
    ordering = ("match", "team", "player")
    autocomplete_fields = ("match", "team", "player")


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = (
        "match",
        "event_index",
        "period",
        "timestamp",
        "minute",
        "event_type_name",
        "team",
        "player",
        "possession",
    )
    list_filter = ("event_type_name", "period", "team", "match")
    search_fields = (
        "external_id",
        "match__external_id",
        "match__home_team__name",
        "match__away_team__name",
        "event_type_name",
        "team__name",
        "player__name",
        "player__nickname",
    )
    ordering = ("match", "event_index")
    autocomplete_fields = ("match", "team", "player")


@admin.register(Match360Frame)
class Match360FrameAdmin(admin.ModelAdmin):
    list_display = ("match", "event_uuid")
    list_filter = ("match",)
    search_fields = (
        "event_uuid",
        "match__external_id",
        "match__home_team__name",
        "match__away_team__name",
    )
    ordering = ("match", "event_uuid")
    autocomplete_fields = ("match",)


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = (
        "started_at",
        "operation",
        "dataset",
        "status",
        "files_seen",
        "records_seen",
        "records_created",
        "records_skipped",
        "finished_at",
    )
    list_filter = ("operation", "dataset", "status", "started_at", "finished_at")
    search_fields = ("operation", "dataset", "source_path", "checkpoint", "error_message")
    ordering = ("-started_at",)
    date_hierarchy = "started_at"
    readonly_fields = (
        "operation",
        "dataset",
        "source_path",
        "status",
        "checkpoint",
        "files_seen",
        "records_seen",
        "records_created",
        "records_skipped",
        "error_message",
        "started_at",
        "finished_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
