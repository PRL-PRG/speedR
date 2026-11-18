# Contributing to speedR

Thanks for helping. This project measures R's performance, so the bar for
changes is that the numbers stay **trustworthy and comparable over time**.
Most of the rules below follow from that.

## Ways to help

- **Report a problem** with the dashboard, a number that looks wrong, or the
  pipeline: open an issue using one of the templates.
- **Ask about a change in R's performance**: use the *Performance question*
  template and link the dashboard page.
- **Propose a benchmark**: benchmarks live in
  [PRL-PRG/r-benchmarks](https://github.com/PRL-PRG/r-benchmarks), not here.
- **Code and docs**: pull requests are welcome. For anything larger than a fix,
  open an issue first so we can agree on the approach.

## Development setup

```sh
uv sync              # Python ≥ 3.12; installs speedr and the dev tools
uv run pytest
uv run ruff check .
```

The dashboard is in `site/` (see its [README](site/README.md)). It renders
synthetic data unless `SPEEDR_RESULTS` points at a results checkout, so you do
not need a benchmark machine to work on it.

## Pull requests

- Keep each PR to one change and explain *why* in the description.
- CI must pass: lint, tests, and a render of the dashboard.
- Add or update tests for pipeline code. For dashboard changes, attach a
  screenshot in light and dark mode.
- Write commit messages in the imperative ("Add arm64 machine"), with a body
  when the reason is not obvious.

## Rules that protect the measurements

1. **Never change a measured thing silently.** Anything that can move the
   numbers (run design, build flags, toolchain image, kernel, the category
   rules) needs an entry in the machine change log or a new config/rules
   version, so the dashboard can mark it.
2. **Speedups only within one machine.** Never divide times measured on
   different machines.
3. **Pinned inputs.** Images by digest, packages from dated snapshots, and the
   suite and `bench` by commit.

## Security

The benchmark machines and the scheduler are **self-hosted GitHub Actions
runners on a public repository**. Code from a pull request must never reach
them:

- Workflows that run on self-hosted runners are triggered only by `schedule`,
  `workflow_dispatch` or `workflow_call` from `main`, never by `pull_request`
  or `pull_request_target`. `tests/test_workflows.py` enforces this.
- Benchmark machines hold no write credentials. Only the scheduler can push to
  speedR-results.

If you find a security problem, please do not open a public issue. Contact
the maintainers privately through GitHub's *Report a vulnerability* button on
the Security tab.

## Licence

By contributing you agree that your contributions are licensed under the
[MIT licence](LICENSE). Results are published under CC0 in speedR-results.
