from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.football.models import IngestionRun
from apps.football.services import (
    discover_files,
    import_competitions,
    import_events,
    import_frames,
    import_lineup,
    import_matches_file,
)

from ._ingestion import begin_run, match_from_root, source_root


class Command(BaseCommand):
    help = "Explicitly ingest one selected dataset; never runs automatically."

    def add_arguments(self, parser):
        parser.add_argument("--root", required=True)
        parser.add_argument("--dataset", choices=("competitions", "matches", "events", "lineups", "three-sixty"), required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--resume", action="store_true")
        parser.add_argument("--force", action="store_true", help="Explicitly reprocess existing records.")
        parser.add_argument(
            "--skip-missing-matches",
            action="store_true",
            help="Skip related-data files whose match metadata is unavailable.",
        )

    def handle(self, *args, **options):
        if options["force"] and not options["dry_run"] and not options["resume"]:
            self.stdout.write(self.style.WARNING("Force mode changes existing records; invocation was explicit."))
        root = source_root(options["root"])
        dataset = options["dataset"]
        files = [item for item in discover_files(root) if item.dataset == dataset]
        if not files:
            raise CommandError(f"No {dataset} files found below {root}")
        run = begin_run("ingest_dataset", dataset, root, options["dry_run"])
        if options["resume"]:
            previous = (
                IngestionRun.objects.filter(
                    operation="ingest_dataset",
                    dataset=dataset,
                    status=IngestionRun.Status.FAILED,
                )
                .order_by("-started_at")
                .first()
            )
            if previous and previous.checkpoint:
                checkpoint_index = next(
                    (index for index, item in enumerate(files) if str(item.path) == previous.checkpoint),
                    -1,
                )
                files = files[checkpoint_index + 1 :]
        try:
            for item in files:
                if options["dry_run"]:
                    self.stdout.write(f"would process {item.path}")
                    run.files_seen += 1
                    continue
                if dataset == "competitions":
                    created, skipped = import_competitions(item.path, force=options["force"])
                elif dataset == "matches":
                    created, skipped = import_matches_file(item.path, force=options["force"])
                else:
                    if item.match_id is None:
                        continue
                    try:
                        match = match_from_root(root, item.match_id, options["force"])
                    except FileNotFoundError as exc:
                        if not options["skip_missing_matches"]:
                            raise
                        self.stderr.write(self.style.WARNING(str(exc)))
                        run.files_seen += 1
                        run.records_skipped += 1
                        run.records_seen += 1
                        run.checkpoint = str(item.path)
                        run.error_message = (
                            f"{run.error_message}\n{exc}".strip()
                        )
                        run.save(
                            update_fields=(
                                "files_seen",
                                "records_seen",
                                "records_skipped",
                                "checkpoint",
                                "error_message",
                            )
                        )
                        continue
                    if dataset == "events":
                        created, skipped = import_events(item.path, match, force=options["force"])
                    elif dataset == "lineups":
                        created, skipped = import_lineup(item.path, match, force=options["force"])
                    else:
                        created, skipped = import_frames(item.path, match, force=options["force"])
                run.files_seen += 1
                run.records_created += created
                run.records_skipped += skipped
                run.records_seen += created + skipped
                run.checkpoint = str(item.path)
                run.save(update_fields=("files_seen", "records_seen", "records_created", "records_skipped", "checkpoint"))
            run.status = IngestionRun.Status.DRY_RUN if options["dry_run"] else IngestionRun.Status.COMPLETED
        except Exception as exc:
            run.status = IngestionRun.Status.FAILED
            run.error_message = str(exc)
            run.finished_at = timezone.now()
            run.save(update_fields=("status", "error_message", "finished_at"))
            raise
        run.finished_at = timezone.now()
        run.save(update_fields=("status", "finished_at"))
        self.stdout.write(self.style.SUCCESS(f"{run.status}: {run.records_seen} records seen"))
