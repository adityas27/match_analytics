from pathlib import Path

from django.core.management.base import CommandError

from apps.football.models import IngestionRun, Match
from apps.football.services import (
    find_match_file,
    import_match_metadata,
    iter_json_array,
)


def source_root(value: str) -> Path:
    root = Path(value).resolve()
    if not root.is_dir():
        raise CommandError(f"Dataset root does not exist: {root}")
    return root


def match_from_root(root: Path, match_id: int, force: bool) -> Match:
    existing = Match.objects.filter(external_id=match_id).first()
    if existing is not None:
        return existing
    path = find_match_file(root, match_id)
    item = next(item for item in iter_json_array(path) if item.get("match_id") == match_id)
    return import_match_metadata(item, str(path), force=force)


def begin_run(operation: str, dataset: str, root: Path, dry_run: bool) -> IngestionRun:
    return IngestionRun.objects.create(
        operation=operation,
        dataset=dataset,
        source_path=str(root),
        status=IngestionRun.Status.DRY_RUN if dry_run else IngestionRun.Status.RUNNING,
    )
