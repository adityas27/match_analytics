from django.core.management.base import BaseCommand

from apps.football.services import discover_files

from ._ingestion import source_root


class Command(BaseCommand):
    help = "List available StatsBomb files without touching the database."

    def add_arguments(self, parser):
        parser.add_argument("--root", required=True, help="StatsBomb data directory.")

    def handle(self, *args, **options):
        files = discover_files(source_root(options["root"]))
        counts = {}
        for item in files:
            counts[item.dataset] = counts.get(item.dataset, 0) + 1
        self.stdout.write(f"Files discovered: {len(files)}")
        for dataset, count in sorted(counts.items()):
            self.stdout.write(f"{dataset}: {count}")
        for item in files[:20]:
            self.stdout.write(f"{item.dataset}: {item.path}")
