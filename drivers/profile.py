"""speedR's profile pass: r-benchmarks' rbench_perf app with speedR's R
command and the VMIL26 recording settings (see common.py).

Always pass --dir: the R process's stdout, which carries the MARK lines the
reduce step needs, is only written by the dir reporter.
"""

from dataclasses import field

import common
import rbench_perf as rp
from bench import ByBenchmarkMetricSummary, Context, FixedRuns, Params, SystemProbe, Time, bench_app

# VMIL26's recipe, which perf-rules.R was validated with. r-benchmarks'
# rbench_perf defaults are 1999 Hz, a 16 kB stack dump and 1 recording.
PERF = {"freq": 999, "stack_size": 32768, "recordings": 5}


class ProfileParams(rp.RbenchProfileParams):
    freq: int = field(default=PERF["freq"], metadata={
        "metavar": "Hz", "help": "perf sampling frequency", "group": rp.PERF_ARG_GROUP})
    stack_size: int = field(default=PERF["stack_size"], metadata={
        "metavar": "bytes", "help": "dwarf stack dump size", "group": rp.PERF_ARG_GROUP})
    recordings: int = field(default=PERF["recordings"], metadata={
        "metavar": "N", "help": "perf recordings (R processes) per benchmark.",
        "group": rp.PERF_ARG_GROUP})
    config: str = field(default="default", metadata={
        "help": "speedR configuration (configs.toml) whose run-time environment to set."})


def command(ctx: Context[Params]) -> list[str]:
    p = ctx.params
    args = [str(rp.rb.BENCHMARKS_FOLDER / ctx.suite / f"{ctx.benchmark}.R"),
            str(p.get_dir() / "marker.so"), str(ctx.data.arg)]
    return common.r_command(p.R, rp.PERF_SUBFOLDER / "harness_instrument.R", args)


# rbench_perf.INSTRUMENT_APP's parts, put together again: its suites leave
# R_LIBS empty (rbench.DEFAULT_APP sets it to the package library), and
# environment set on the app cannot override what the suites set.
APP = (
    bench_app(params=ProfileParams)
    .add(rp.rb.ALL_SUITES.with_env(lambda ctx: {"R_LIBS": str(ctx.params.get_library_path)}))
    .with_command(command)
    .with_env(lambda ctx: common.config_env(ctx.params.config))
    .with_hook(lambda ctx: ctx.params.get_install_packages_hook)
    .with_runs(lambda ctx: FixedRuns(ctx.params.recordings))
    .with_controller(rp.get_perf)
    .with_hook(lambda ctx: rp.CompileMarkerHook(ctx.params.R, ctx.params.get_dir()))
    .with_metric(Time(), rp.MarkMetric())
    .with_probe(SystemProbe())
    .with_summary(ByBenchmarkMetricSummary().on_metrics("elapsed"))
)

if __name__ == "__main__":
    APP.main()
