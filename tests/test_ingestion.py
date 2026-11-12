import json

import pytest
from django.core.management import call_command

from apps.football.models import IngestionRun
from apps.football.parsers import iter_json_array
from apps.football.services import discover_files


def test_streaming_parser_reads_array(tmp_path):
    source = tmp_path / "items.json"
    source.write_text(json.dumps([{"id": 1, "value": 1.25}, {"id": 2}]), encoding="utf-8")

    assert list(iter_json_array(source)) == [{"id": 1, "value": 1.25}, {"id": 2}]


def test_dataset_discovery_finds_supported_layout(tmp_path):
    (tmp_path / "competitions.json").write_text("[]", encoding="utf-8")
    (tmp_path / "matches").mkdir()
    (tmp_path / "matches" / "11").mkdir()
    (tmp_path / "matches" / "11" / "1.json").write_text("[]", encoding="utf-8")
    (tmp_path / "events").mkdir()
    (tmp_path / "events" / "123.json").write_text("[]", encoding="utf-8")

    discovered = discover_files(tmp_path)

    assert {(item.dataset, item.match_id) for item in discovered} == {
        ("competitions", None),
        ("matches", None),
        ("events", 123),
    }


@pytest.mark.django_db
def test_ingest_dataset_dry_run_does_not_create_domain_records(tmp_path):
    (tmp_path / "competitions.json").write_text("[]", encoding="utf-8")

    call_command(
        "ingest_dataset",
        "--root",
        str(tmp_path),
        "--dataset",
        "competitions",
        "--dry-run",
    )

    run = IngestionRun.objects.get()
    assert run.status == IngestionRun.Status.DRY_RUN
    assert run.records_seen == 0


@pytest.mark.django_db
def test_ingest_dataset_can_explicitly_skip_missing_match_metadata(tmp_path):
    (tmp_path / "events").mkdir()
    (tmp_path / "events" / "3890259.json").write_text("[]", encoding="utf-8")

    call_command(
        "ingest_dataset",
        "--root",
        str(tmp_path),
        "--dataset",
        "events",
        "--skip-missing-matches",
    )

    run = IngestionRun.objects.get()
    assert run.status == IngestionRun.Status.COMPLETED
    assert run.records_skipped == 1
    assert "3890259" in run.error_message
