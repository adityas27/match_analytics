import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from django.db import transaction

from .models import (
    Competition,
    Match,
    Match360Frame,
    MatchEvent,
    MatchPlayer,
    Player,
    Season,
    Team,
)
from .parsers import iter_json_array

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatasetFile:
    dataset: str
    path: Path
    match_id: int | None = None


def discover_files(root: Path) -> list[DatasetFile]:
    result = [DatasetFile("competitions", root / "competitions.json")]
    for dataset in ("matches", "events", "lineups", "three-sixty"):
        for path in sorted((root / dataset).rglob("*.json")):
            match_id = int(path.stem) if dataset != "matches" and path.stem.isdigit() else None
            result.append(DatasetFile(dataset, path, match_id))
    return [item for item in result if item.path.exists()]


def _entity(manager, external_id: int, defaults: dict[str, Any], force: bool):
    if force:
        obj, created = manager.update_or_create(external_id=external_id, defaults=defaults)
    else:
        obj, created = manager.get_or_create(external_id=external_id, defaults=defaults)
    return obj, created


def _date(value: str | None):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def _time(value: str | None):
    return datetime.strptime(value.split(".")[0], "%H:%M:%S").time() if value else None


def import_competitions(path: Path, force: bool = False) -> tuple[int, int]:
    created = skipped = 0
    for item in iter_json_array(path):
        _, was_created = _entity(
            Competition.objects,
            item["competition_id"],
            {
                "name": item["competition_name"],
                "country_name": item.get("country_name", ""),
                "gender": item.get("competition_gender", ""),
                "international": item.get("competition_international"),
                "youth": item.get("competition_youth"),
                "raw_data": item,
            },
            force,
        )
        created += was_created
        skipped += not was_created
    return created, skipped


def import_matches_file(path: Path, force: bool = False) -> tuple[int, int]:
    created = skipped = 0
    for item in iter_json_array(path):
        exists = Match.objects.filter(external_id=item["match_id"]).exists()
        import_match_metadata(item, str(path), force=force)
        if exists:
            skipped += 1
        else:
            created += 1
    return created, skipped


def _team(data: dict[str, Any], force: bool) -> Team:
    team, _ = _entity(
        Team.objects,
        data["home_team_id"] if "home_team_id" in data else data["away_team_id"],
        {
            "name": data.get("home_team_name", data.get("away_team_name", "")),
            "gender": data.get("home_team_gender", data.get("away_team_gender", "")),
            "country_name": (data.get("country") or {}).get("name", ""),
            "raw_data": data,
        },
        force,
    )
    return team


@transaction.atomic
def import_match_metadata(item: dict[str, Any], source_path: str, force: bool = False) -> Match:
    competition_data = item["competition"]
    season_data = item["season"]
    competition, _ = _entity(
        Competition.objects,
        competition_data["competition_id"],
        {"name": competition_data["competition_name"], "raw_data": competition_data},
        force,
    )
    season, _ = _entity(
        Season.objects,
        season_data["season_id"],
        {"name": season_data["season_name"], "raw_data": season_data},
        force,
    )
    home = _team(item["home_team"], force)
    away = _team(item["away_team"], force)
    match, _ = _entity(
        Match.objects,
        item["match_id"],
        {
            "competition": competition,
            "season": season,
            "home_team": home,
            "away_team": away,
            "match_date": _date(item.get("match_date")),
            "kick_off": _time(item.get("kick_off")),
            "home_score": item.get("home_score"),
            "away_score": item.get("away_score"),
            "match_status": item.get("match_status", ""),
            "match_status_360": item.get("match_status_360", ""),
            "match_week": item.get("match_week"),
            "raw_data": item,
            "source_path": source_path,
        },
        force,
    )
    return match


def _ensure_player(data: dict[str, Any], force: bool) -> Player:
    player, _ = _entity(
        Player.objects,
        data["player_id"] if "player_id" in data else data["id"],
        {
            "name": data.get("player_name", data.get("name", "")),
            "nickname": data.get("player_nickname", data.get("nickname", "")) or "",
            "country_name": (data.get("country") or {}).get("name", ""),
            "raw_data": data,
        },
        force,
    )
    return player


def import_lineup(path: Path, match: Match, force: bool = False) -> tuple[int, int]:
    created = skipped = 0
    for team_data in iter_json_array(path):
        team, _ = _entity(
            Team.objects,
            team_data["team_id"],
            {"name": team_data["team_name"], "raw_data": team_data},
            force,
        )
        for player_data in team_data.get("lineup", []):
            player = _ensure_player(player_data, force)
            defaults = {
                "jersey_number": player_data.get("jersey_number"),
                "cards": player_data.get("cards", []),
                "positions": player_data.get("positions", []),
                "raw_data": player_data,
            }
            if force:
                _, was_created = MatchPlayer.objects.update_or_create(
                    match=match, team=team, player=player, defaults=defaults
                )
            else:
                _, was_created = MatchPlayer.objects.get_or_create(
                    match=match, team=team, player=player, defaults=defaults
                )
            created += was_created
            skipped += not was_created
    return created, skipped


def import_events(path: Path, match: Match, force: bool = False) -> tuple[int, int]:
    created = skipped = 0
    for item in iter_json_array(path):
        team_data = item.get("team") or {}
        player_data = item.get("player")
        team = None
        player = None
        if team_data.get("id"):
            team, _ = _entity(Team.objects, team_data["id"], {"name": team_data.get("name", "")}, force)
        if player_data and player_data.get("id"):
            player = _ensure_player(player_data, force)
        defaults = {
            "match": match,
            "event_index": item.get("index", 0),
            "period": item.get("period"),
            "timestamp": _time(item.get("timestamp")),
            "minute": item.get("minute"),
            "second": item.get("second"),
            "event_type_id": (item.get("type") or {}).get("id"),
            "event_type_name": (item.get("type") or {}).get("name", "Unknown"),
            "team": team,
            "player": player,
            "possession": item.get("possession"),
            "possession_team_id": (item.get("possession_team") or {}).get("id"),
            "location": item.get("location"),
            "payload": {key: value for key, value in item.items() if key not in {"id", "type"}},
            "raw_data": item,
        }
        if force:
            _, was_created = MatchEvent.objects.update_or_create(
                external_id=UUID(item["id"]), defaults=defaults
            )
        else:
            _, was_created = MatchEvent.objects.get_or_create(
                external_id=UUID(item["id"]), defaults=defaults
            )
        created += was_created
        skipped += not was_created
    return created, skipped


def import_frames(path: Path, match: Match, force: bool = False) -> tuple[int, int]:
    created = skipped = 0
    for item in iter_json_array(path):
        defaults = {
            "match": match,
            "visible_area": item.get("visible_area", []),
            "freeze_frame": item.get("freeze_frame", []),
            "raw_data": item,
        }
        if force:
            _, was_created = Match360Frame.objects.update_or_create(
                event_uuid=UUID(item["event_uuid"]), defaults=defaults
            )
        else:
            _, was_created = Match360Frame.objects.get_or_create(
                event_uuid=UUID(item["event_uuid"]), defaults=defaults
            )
        created += was_created
        skipped += not was_created
    return created, skipped


def find_match_file(root: Path, match_id: int) -> Path:
    for path in (root / "matches").rglob("*.json"):
        for item in iter_json_array(path):
            if item.get("match_id") == match_id:
                return path
    raise FileNotFoundError(f"Match {match_id} was not found below {root / 'matches'}")
