from django.core.management.base import BaseCommand

from apps.football.models import Match, MatchEvent, MatchPlayer


class Command(BaseCommand):
    help = "Report relational integrity counts; does not modify data."

    def handle(self, *args, **options):
        self.stdout.write(f"matches={Match.objects.count()}")
        self.stdout.write(f"events={MatchEvent.objects.count()}")
        self.stdout.write(f"lineup_players={MatchPlayer.objects.count()}")
        orphan_events = MatchEvent.objects.filter(match__isnull=True).count()
        orphan_lineups = MatchPlayer.objects.filter(match__isnull=True).count()
        if orphan_events or orphan_lineups:
            self.stderr.write(self.style.ERROR(f"orphan_events={orphan_events} orphan_lineups={orphan_lineups}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("validation passed"))
