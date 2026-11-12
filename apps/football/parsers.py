from collections.abc import Iterator
from pathlib import Path
from typing import Any

import ijson


def iter_json_array(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("rb") as source:
        # JSONField accepts JSON-native numeric values, while ijson otherwise
        # represents decimal numbers as Decimal instances.
        yield from ijson.items(source, "item", use_float=True)


def read_json_array(path: Path) -> list[dict[str, Any]]:
    return list(iter_json_array(path))
