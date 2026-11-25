"""`speedr` command line: the registry, the metadata schema, the suite pin,
build settings, the sentinel, the profile manifest, the passes of a run and the
ingest."""

import argparse
import json
import sys
from pathlib import Path

from . import (
    __version__,
    build,
    configs,
    ingest,
    machines,
    meta,
    methodology,
    profile,
    results,
    sentinel,
    upstream,
)


def cmd_machines(args: argparse.Namespace) -> int:
    for m in machines.load_all():
        print(f"{m.name:24} {m.os}/{m.arch:8} wake={m.wake:9} profiler={m.profiler:7} "
              f"sentinel={'calibrated' if m.sentinel else 'uncalibrated'}")
    return 0


def cmd_configs(args: argparse.Namespace) -> int:
    for c in configs.load_all().values():
        print(f"{c.name:12} {c.status:8} {c.description}")
    return 0


def cmd_methodology(args: argparse.Namespace) -> int:
    if args.current:
        print(methodology.current().version)
        return 0
    for m in methodology.load_all():
        print(f"{m.version:6} {m.status:7} {m.date}  {m.summary}")
    return 0


def cmd_build_env(args: argparse.Namespace) -> int:
    for k, v in build.environment(args.version).items():
        print(f"{k}={v}")
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


def cmd_sentinel(args: argparse.Namespace) -> int:
    if args.plan:
        print(sentinel.plan())
        return 0
    r = sentinel.check(json.loads(Path(args.report).read_text()), args.machine)
    print(json.dumps(r, indent=1))
    return 3 if r["status"] == "failed" else 0


def cmd_ingest(args: argparse.Namespace) -> int:
    for run in ingest.ingest(Path(args.spool), Path(args.root)):
        print(run)
    return 0


def cmd_merge_passes(args: argparse.Namespace) -> int:
    reports = [json.loads(Path(f).read_text()) for f in args.reports]
    json.dump(ingest.merge_passes(reports), sys.stdout)
    return 0


def cmd_suite(args: argparse.Namespace) -> int:
    for name, commit in upstream.commits().items():
        print(f"{name:7} {commit}")
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
    mv = sub.add_parser("methodology", help="list the methodology versions")
    mv.add_argument("--current", action="store_true", help="print only the one new runs use")
    mv.set_defaults(func=cmd_methodology)
    b = sub.add_parser("build-env", help="the compilers and configure answers to build an R "
                       "version with (build/settings.toml)")
    b.add_argument("version",
                   help='a VERSION file\'s line, e.g. 4.6.2 or "4.7.0 Under development"')
    b.set_defaults(func=cmd_build_env)
    v = sub.add_parser("validate-meta", help="check meta.json files against the schema")
    v.add_argument("files", nargs="+", metavar="meta.json")
    v.set_defaults(func=cmd_validate_meta)
    r = sub.add_parser("check-results", help="check a speedR-results checkout's layout")
    r.add_argument("root", metavar="DIR")
    r.set_defaults(func=cmd_check_results)
    s = sub.add_parser("sentinel", help="check a sentinel run against the machine's reference "
                       "(exit 3: failed)")
    s.add_argument("report", nargs="?", metavar="REPORT.json", help="the sentinel's --json report")
    s.add_argument("machine", nargs="?", help="machines/<MACHINE>.toml")
    s.add_argument("--plan", action="store_true",
                   help="print the R version, benchmarks and run design as shell assignments")
    s.set_defaults(func=cmd_sentinel)
    i = sub.add_parser("ingest", help="add the spool's new runs to a speedR-results checkout")
    i.add_argument("spool", metavar="SPOOL")
    i.add_argument("root", metavar="RESULTS")
    i.set_defaults(func=cmd_ingest)
    mp = sub.add_parser("merge-passes", help="one report of a run's passes, one per code "
                        "layout: the k-th pass becomes process k")
    mp.add_argument("reports", nargs="+", metavar="REPORT.json")
    mp.set_defaults(func=cmd_merge_passes)
    sub.add_parser("suite", help="show the rbench and bench commits, checked against the "
                   "environment").set_defaults(func=cmd_suite)
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
    except (machines.MachineError, configs.ConfigError, methodology.MethodologyError,
            build.BuildError,
            upstream.UpstreamError) as e:
        print(f"speedr: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
