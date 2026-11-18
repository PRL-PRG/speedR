# Benchmark machines

A benchmark machine is a dedicated box that runs one GitHub Actions
self-hosted runner. It sleeps (powered off) when idle; an always-on
**scheduler** wakes it when work is queued.

## Adding a machine

1. Prepare the host (below for Linux).
2. Add `machines/<name>.toml` (copy an existing one). `name` must equal the
   file name and is also the runner label `m-<name>`. Run
   `uv run speedr machines` to validate.
3. Register the runner with the labels `speedr machines` prints
   (`self-hosted, speedr, m-<name>, os-<os>, arch-<arch>`).
4. Store the wake secret (MAC address or BMC host) as the Actions secret named
   by `wake_secret`. Never commit it.
5. New platforms start with `profiles = "experimental"` until their profiler is
   validated against perf on Linux x86-64.

### Registry fields

| field | values | meaning |
|---|---|---|
| `os`, `arch` | `linux`/`macos`/`windows`, `x86_64`/`aarch64` | platform |
| `runtime` | `docker`, `native` | Docker images on Linux; native toolchains elsewhere |
| `profiler` | `perf`, `samply`, `xctrace`, `etw`, `none` | how profiles are recorded |
| `profiles` | `validated`, `experimental`, `none` | shown as a badge on the dashboard |
| `wake` | `wol`, `ipmi`, `relay`, `always-on`, `manual` | how the scheduler wakes it |
| `wake_secret` | Actions secret name | MAC (wol, relay) or BMC host (ipmi) |
| `relay_host` | host name | for `relay`: an always-on host on the machine's subnet |
| `cores`, `numa_node` | cpuset, node | where benchmarks are pinned |
| `track_devel` | bool | benchmark every R-devel night |

### Wake methods

- **wol**: Wake-on-LAN magic packet from the scheduler. Needs the scheduler on
  the same L2 segment (or a router forwarding directed broadcasts).
- **ipmi**: `ipmitool power on` against the board's BMC (or AMT, iDRAC, iLO).
  Routable, and also reports power state. Preferred when available.
- **relay**: the magic packet is sent over SSH from another always-on host on
  the machine's subnet.
- **always-on**: never sleeps.

## Linux x86-64 host setup

**OS:** Ubuntu Server 26.04 LTS, minimal install, no desktop, GA kernel. The
host provides only the kernel, perf, Docker and the runner; the toolchain is in
the images.

- **Freeze:** `apt-mark hold` the kernel, `linux-tools-*` and Docker packages;
  disable `unattended-upgrades`. Update only in maintenance windows, and log
  each update as a machine change.
- **Remove noise:** remove snapd and cloud-init; disable the apt-daily,
  man-db, fstrim, plocate and motd-news timers.
- **Kernel command line:** `isolcpus=`, `nohz_full=` and `rcu_nocbs=` for the
  benchmark cores; keep `irqbalance` off them.
- **BIOS:** Wake-on-LAN from S5 on; SMT off; record the BIOS version and fan
  profile. Turbo is left to `bench denoise`.
- **NIC:** WoL `g`, persisted in netplan (`wakeonlan: true`).
- **Storage:** a separate partition of ~300 GB for `/var/lib/docker` and
  `/var/lib/speedr` (build cache, scratch).
- **Services:** chrony; the runner as a systemd service; a boot unit running
  `bench denoise`; the idle power-off timer (powers off after 20 min without a
  job).

*(To do: an Ansible role for this, and the macOS and Windows equivalents.)*
