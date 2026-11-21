"""speedR's timing pass: r-benchmarks' default app with speedR's R command,
run design and configuration environment (see common.py)."""

from dataclasses import field

import common
import rbench as rb
from bench import Context, Params, Thermal

# r-benchmarks' own defaults are 3 runs x 5 iterations, 2 of them warm-up.
RUN_DESIGN = {"runs": 3, "iterations": 5, "warmups": 1}   # methodology 0.2


class TimingParams(rb.RbenchHarnessParams):
    runs: int = field(default=RUN_DESIGN["runs"], metadata={
        "metavar": "N", "help": "Measure each benchmark in N separate R processes."})
    iterations: int = field(default=RUN_DESIGN["iterations"], metadata={
        "metavar": "N", "help": "Iterations inside each process, warm-up included."})
    warmups: int = field(default=RUN_DESIGN["warmups"], metadata={
        "metavar": "N", "help": "Iterations discarded at the start of each process."})
    config: str = field(default="default", metadata={
        "help": "speedR configuration (configs.toml) whose run-time environment to set."})


def command(ctx: Context[Params]) -> list[str]:
    p = ctx.params
    args = [str(rb.BENCHMARKS_FOLDER / ctx.suite / f"{ctx.benchmark}.R"),
            str(p.iterations), str(ctx.data.arg)]
    if p.profile is not None:
        args.append(str(p.profile))
    return common.r_command(p.R, rb.BENCHMARKS_FOLDER / "harness.R", args)


# CPU temperature and throttling around every execution: samples cpu_temp_max
# and cpu_throttle, flagged `suspect` when the CPU throttled or ran near its limit
THERMAL = Thermal()

APP = (
    rb.DEFAULT_APP.with_params(TimingParams)
    .with_command(command, override=True)
    .with_env(lambda ctx: common.config_env(ctx.params.config))
    .with_hook(THERMAL)
    .with_metric(THERMAL)
)

if __name__ == "__main__":
    APP.main()
