"""`speedr` command line. Grows a subcommand per pipeline stage (build, run,
profile, ingest, ...); for now it covers the registry, the metadata schema, the
pinned suite and the profile manifest."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__, configs, machines, meta, profile, results, upstream


def cmd_machines(args: argparse.Namespace) -> int:
    for m in machines.load_all():
        print(f"{m.name:24} {m.os}/{m.arch:8} wake={m.wake:9} profiler={m.profiler:7} "
              f"labels={','.join(m.runner_labels)}")
    return 0


def cmd_configs(args: argparse.Namespace) -> int:
    for c in configs.load_all().values():
        print(f"{c.name:12} {c.status:8} {c.description}")
    return 0


def cmd_validate_meta(args: argparse.Namespace) -> int:
    bad = 0
    for path in args.files:
        errs = meta.errors(json.loads(Path(path).read_text()))
        for e in errs:
            print(f"{path}: {e}", file=sys.stderr)
        bad += bool(errs)
    return 1 if bad else 0


def cmd_check_results(args: argparse.Namespace) -> int:
    problems = results.check(Path(args.root))
    for p in problems:
        print(p, file=sys.stderr)
    if not problems:
        print(f"{args.root}: ok")
    return 1 if problems else 0


def cmd_fetch_suite(args: argparse.Namespace) -> int:
    p = upstream.pin()
    dest = upstream.checkout(Path(args.dest), p)
    print(f"r-benchmarks {p.commit} in {dest}")
    print(f"bench        {upstream.bench_commit(dest)} (r-benchmarks' uv.lock)")
    return 0


def cmd_profile_manifest(args: argparse.Namespace) -> int:
    rows, problems = profile.manifest(Path(args.report), Path(args.dir))
    for p in problems:
        print(p, file=sys.stderr)
    profile.write_manifest(rows, Path(args.out))
    print(f"{args.out}: {len(rows)} recording(s), {len(problems)} missing")
    return 0 if rows else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="speedr", description=__doc__)
    p.add_argument("--version", action="version", version=f"speedr {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("machines", help="list and validate machines/*.toml").set_defaults(
        func=cmd_machines)
    sub.add_parser("configs", help="list and validate configs.toml").set_defaults(
        func=cmd_configs)
    v = sub.add_parser("validate-meta", help="check meta.json files against the schema")
    v.add_argument("files", nargs="+", metavar="meta.json")
    v.set_defaults(func=cmd_validate_meta)
    r = sub.add_parser("check-results", help="check an speedR-results checkout's layout")
    r.add_argument("root", metavar="DIR")
    r.set_defaults(func=cmd_check_results)
    f = sub.add_parser("fetch-suite",
                       help="check out the r-benchmarks commit pinned in upstream.toml")
    f.add_argument("dest", metavar="DIR")
    f.set_defaults(func=cmd_fetch_suite)
    pm = sub.add_parser("profile-manifest",
                        help="list a profile pass's recordings for categories/categorize.R")
    pm.add_argument("report", metavar="REPORT.json", help="the pass's --json report")
    pm.add_argument("dir", metavar="DIR", help="the pass's --dir")
    pm.add_argument("out", metavar="MANIFEST.csv")
    pm.set_defaults(func=cmd_profile_manifest)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (machines.MachineError, configs.ConfigError, upstream.UpstreamError) as e:
        print(f"speedr: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
