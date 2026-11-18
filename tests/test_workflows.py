"""Security rules for workflows (docs/guidelines.md#security).

The benchmark machines and the scheduler are self-hosted runners on a public
repository. A workflow that can be started by a pull request would run a
stranger's code on them, so no workflow that targets a self-hosted runner may
be triggered by pull_request or pull_request_target.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
UNSAFE = {"pull_request", "pull_request_target"}


def triggers(doc: dict) -> set[str]:
    on = doc.get("on", doc.get(True))     # PyYAML reads a bare `on:` key as True
    if isinstance(on, str):
        return {on}
    return set(on or ())


GITHUB_HOSTED = ("ubuntu-", "macos-", "windows-")


def runs_on_self_hosted(doc: dict) -> bool:
    """True unless every job names a GitHub-hosted image outright. A label
    computed from an expression or a matrix counts as self-hosted: we cannot
    tell where it lands, so it gets the strict rule."""
    for job in (doc.get("jobs") or {}).values():
        if "uses" in job:
            # a called workflow runs with the caller's trigger, so it counts
            # as self-hosted if it is; one from another repository is unknown
            ref = job["uses"]
            if not ref.startswith("./"):
                return True
            called = yaml.safe_load((ROOT / ref).read_text())
            if runs_on_self_hosted(called):
                return True
            continue
        labels = job.get("runs-on", "")
        labels = labels if isinstance(labels, list) else [labels]
        if not all(isinstance(x, str) and x.startswith(GITHUB_HOSTED) for x in labels):
            return True
    return False


def test_there_are_workflows():
    assert WORKFLOWS


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_self_hosted_workflows_never_run_for_pull_requests(path):
    doc = yaml.safe_load(path.read_text())
    if runs_on_self_hosted(doc):
        assert not triggers(doc) & UNSAFE, f"{path.name} runs on self-hosted and is PR-triggered"


def test_the_rule_catches_violations():
    pr_on_bench = {"on": {"pull_request": None},
                   "jobs": {"b": {"runs-on": ["self-hosted", "speedr"]}}}
    matrix_label = {True: ["pull_request"],
                    "jobs": {"b": {"runs-on": "${{ matrix.machine }}"}}}
    hosted = {"on": "pull_request", "jobs": {"t": {"runs-on": "ubuntu-24.04"}}}
    assert runs_on_self_hosted(pr_on_bench) and triggers(pr_on_bench) & UNSAFE
    assert runs_on_self_hosted(matrix_label) and triggers(matrix_label) & UNSAFE
    assert not runs_on_self_hosted(hosted)
