from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.football.models import IngestionRun
from apps.football.services import (
    find_match_file,
    import_events,
    import_frames,
    import_lineup,
)

from ._ingestion import begin_run, match_from_root, source_root


class Command(BaseCommand):
    help = "Explicitly import one match and its available related files."

    def add_arguments(self, parser):
        parser.add_argument("--root", required=True)
        parser.add_argument("--match-id", type=int, required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        root = source_root(options["root"])
        match_id = options["match_id"]
        metadata_path = find_match_file(root, match_id)
        related = [
            root / "events" / f"{match_id}.json",
            root / "lineups" / f"{match_id}.json",
            root / "three-sixty" / f"{match_id}.json",
        ]
        existing_related = [path for path in related if path.exists()]
        run = begin_run("import_match", str(match_id), root, options["dry_run"])
        if options["dry_run"]:
            self.stdout.write(f"would process {metadata_path}")
            for path in existing_related:
                self.stdout.write(f"would process {path}")
            return
        try:
            match = match_from_root(root, match_id, options["force"])
            for path in existing_related:
                if path.parent.name == "events":
                    created, skipped = import_events(path, match, options["force"])
                elif path.parent.name == "lineups":
                    created, skipped = import_lineup(path, match, options["force"])
                else:
                    created, skipped = import_frames(path, match, options["force"])
                run.records_created += created
                run.records_skipped += skipped
                run.records_seen += created + skipped
                run.files_seen += 1
                run.checkpoint = str(path)
            run.status = IngestionRun.Status.COMPLETED
        except Exception as exc:
            run.status = IngestionRun.Status.FAILED
            run.error_message = str(exc)
            raise
        finally:
            run.finished_at = timezone.now()
            run.save()
        self.stdout.write(self.style.SUCCESS(f"completed match {match_id}"))
