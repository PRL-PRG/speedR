"""meta.json: the description of one run, validated against schema/meta.schema.json
before the scheduler ingests it into speedR-results."""

import json
from functools import cache
from pathlib import Path

import jsonschema

SCHEMA_FILE = Path(__file__).resolve().parent / "schema" / "meta.schema.json"


@cache
def schema() -> dict:
    return json.loads(SCHEMA_FILE.read_text())


def errors(meta: dict) -> list[str]:
    """Every schema violation, as `path: message`; empty when valid."""
    v = jsonschema.Draft202012Validator(schema(), format_checker=jsonschema.FormatChecker())
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(v.iter_errors(meta), key=lambda e: list(e.absolute_path))]
