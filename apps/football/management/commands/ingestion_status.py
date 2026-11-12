from django.core.management.base import BaseCommand

from apps.football.models import IngestionRun


class Command(BaseCommand):
    help = "Show ingestion runs and checkpoints."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        for run in IngestionRun.objects.order_by("-started_at")[: options["limit"]]:
            self.stdout.write(
                f"{run.id} {run.status} {run.operation} {run.dataset} "
                f"files={run.files_seen} records={run.records_seen} checkpoint={run.checkpoint}"
            )
