# AGENTS.md

This file contains guidance for coding agents when helping with development in
this repository.

## What is included in this repository

This repository builds the **`redhat-cloud-client-configuration`** RPM (often
abbreviated **RHCCC**). The package wires cloud VM images for automatic
registration with Red Hat services when an RHSM consumer certificate appears at
`/etc/pki/consumer/cert.pem`.

On first boot (or when the cert is created), path units trigger:

- **Insights** registration (`insights-client --register`)
- **RHC / remote host connectivity** — `rhcd` on RHEL 8–9, `yggdrasil` on
  RHEL 10+ (see [rhc](https://github.com/RedHatInsights/rhc) and
  [yggdrasil](https://github.com/redhatinsights/yggdrasil); those daemons ship
  in separate RPMs)
- **Unregister / cleanup** paths when the consumer cert is removed

The RPM ships two **mutually exclusive** subpackages (see the spec file):

| Subpackage | Use case |
|------------|----------|
| `redhat-cloud-client-configuration` (base) | RHUI images — disables `manage_repos`, content from RHUI |
| `redhat-cloud-client-configuration-cdn` | CDN images — enables `manage_repos`, tighter auto-reg intervals, disables RHUI `.repo` files via `rhccc-disable-rhui-repos.py` |

There is no application runtime in this repo — only systemd unit templates,
presets, one Python helper script, and RPM packaging logic.

| Path | Purpose |
|------|---------|
| `*.in` | systemd unit/path templates; `@bindir@`, `@sysconfdir@`, `@libexecdir@` are substituted in `%build` |
| `80-*.preset` | systemd presets that enable the path units |
| `insights-register*.in`, `insights-unregister*.in`, `insights-unregistered*.in` | Insights auto-register / unregister path units and services |
| `rhcd*.in` | RHC daemon (`rhcd`) path units for RHEL 8–9 |
| `yggdrasil*.in` | Yggdrasil daemon path units for RHEL 10+ |
| `rhccc-disable-rhui-repos.py` | CDN helper — disables RHUI mirrorlist/baseurl repos under `/etc/yum.repos.d/` |
| `rhccc-disable-rhui-repos.service.in` | oneshot service run on first boot (CDN subpackage) |
| `redhat-cloud-client-configuration.spec` | RPM spec: `%build` templating, `%post`/`%preun` rhsm.conf changes, subpackage split |
| `.tito/` | [tito](https://github.com/rpm-software-management/tito) release configuration |
| `.packit.yaml` | Packit COPR build targets |
| `LICENSE` | GPL-2.0-or-later |
| `README.md` | Brief build instructions |

Platform branching in the spec: RHEL 10 and Fedora use **`yggdrasil`** unit file
names; RHEL 8–9 use **`rhcd`**. The SRPM must list both sets of sources because
COPR may build the SRPM on a different platform than the target chroot.

## Building

Building is described in [README.md](README.md). Production builds use **tito**
and **rpmbuild**; there is no compile step beyond `sed` substitution of unit
templates.

Prerequisites: `tito`, `rpm-build`, `systemd` (for `%systemd_*` macros in the
spec).

```bash
tito build --test --rpm --verbose --debug -o /tmp/tito_build --no-cleanup
```

Use `tito build` for local RPM verification. Do **not** run `tito tag` or
create commits with the `Automatic commit of package …` prefix — release
tagging is maintainer-only and affects version/release numbering across the
tree.

Install the resulting RPM on a test host to exercise `%post` scriptlets and
systemd units. Packit triggers COPR builds on pull requests and on `main`
commits — see [`.packit.yaml`](.packit.yaml) (targets: CentOS Stream 8–10,
RHEL 7–10, Fedora; `main`-branch COPR jobs omit RHEL 7).

Downstream distro packaging lives in
[gitlab.com/redhat/centos-stream/rpms/redhat-cloud-client-configuration](https://gitlab.com/redhat/centos-stream/rpms/redhat-cloud-client-configuration).

## Testing

This repository has **no in-tree unit or integration tests**. Validation is
RPM install/remove on a cloud-shaped system plus end-to-end auto-registration
flows.

### Local checks before submitting

1. Build the RPM with tito (above) and confirm `%build` produces all expected
   unit files for the target RHEL major (rhcd vs yggdrasil naming).
2. After installing on a test VM, verify presets and path units:
   `systemctl is-enabled insights-register.path` (and the rhcd/yggdrasil path
   units as appropriate).
3. For Python changes, run the script against a fixture `.repo` directory:
   `python3 rhccc-disable-rhui-repos.py /path/to/test-repos.d/`

### End-to-end (cloud auto-registration)

Full auto-registration behavior is validated on cloud VM images (AWS, Azure,
GCP) after RPM install and reboot: `rhsmcertd` auto-registration,
`insights-client` registration, and `rhcd` or `yggdrasil` startup when the
consumer cert appears. Exercise this manually on a test instance or through your
team's cloud test infrastructure when changing units, scriptlets, or the Python
helper.

There are no GitHub Actions workflows in this repository — CI is Packit COPR
builds (see [`.packit.yaml`](.packit.yaml)).

## Security

RHCCC installs **system-wide systemd units** and runs **root-owned `%post`
scriptlets** that modify `/etc/rhsm/rhsm.conf`, restart `rhsmcertd`, and (CDN
subpackage) rewrite files under `/etc/yum.repos.d/`. When modifying or
generating code:

- Do not log or commit RHSM consumer certificates, keys, or registration tokens.
- `%post` scriptlets must only change `rhsm.conf` keys documented in the spec
  and must preserve/restore state via `/etc/rhsm/rhsm.conf.cloud_save` on
  package removal.
- `rhccc-disable-rhui-repos.py` must only disable repos whose mirrorlist/baseurl
  contains `/rhui/`; avoid broad file writes or path traversal — operate only on
  explicit `.repo` paths passed as arguments.
- systemd units should keep minimal privileges; do not broaden `ExecStart`
  commands or drop-in recommendations without review.
- Path units watch `/etc/pki/consumer/cert.pem` — treat cert presence as the
  registration gate, not a trigger for arbitrary commands.

## Code style and architecture

- **Python 3** — `rhccc-disable-rhui-repos.py` uses stdlib only
  (`configparser`, `pathlib`). Keep it portable across RHEL Python versions.
  Use `interpolation=None` so `%` in URLs is not treated as interpolation.
  `.repo` files are INI-like but can be non-standard (e.g. duplicate keys in a
  section); when touching this script, consider `strict=False` so
  `configparser` tolerates that and takes the last value.
- **systemd units** — follow the header/comment style of the existing `*.in`
  files (drop-in override guidance, `Documentation=` links). Placeholders:
  `@bindir@`, `@sysconfdir@`, `@libexecdir@` (expanded in `%build`). The spec
  selects different templates per platform — for example
  `insights-register-cgroupv1.service.in` on RHEL 7 (`MemoryLimit`) vs
  `insights-register.service.in` on RHEL 8+ (`MemoryHigh` / `MemoryMax`), and
  `rhcd*.in` vs `yggdrasil*.in` by major version. Keep cgroup and memory
  directives consistent with the target RHEL release when editing either variant.
- **RPM spec** — use `%if 0%{?rhel}` / `%{?fedora}` conditionals for
  platform-specific units; keep base and `cdn` subpackage `%post` logic in sync
  where behavior must match. Use strict grep patterns when reading
  `subscription-manager config --list` output (anchored regexes with `$`).
- **Presets** — one `enable` line per path unit; preset file names use the
  `80-` prefix for ordering.

## Pull requests

- Link related GitHub issues in the PR description when applicable.
- Ensure the Packit COPR build succeeds for affected targets.
- For behavior changes, note which subpackage (base vs cdn) and which RHEL
  majors are impacted (rhcd vs yggdrasil).
- Request review from a maintainer before merging.

## Git commits

Follow [Conventional Commits](https://www.conventionalcommits.org):

- Subject completes: "when applied, this commit will…"
- Subject and body are separated by a blank line.
- Body expands with relevant detail; detail items start with `* `.
- When a commit relates to a GitHub issue, reference it in the body (e.g.
  `Fixes #123`).
- Commits must be **signed** (`git commit -s -S`).

Example:

```text
docs: add AGENTS.md for AI-assisted development

* Summarize build, test, CI, and contribution conventions for coding agents

Signed-off-by: Your Name <you@redhat.com>
```

Tito release commits (`Automatic commit of package …`) are created by
maintainers via `tito tag`. Do not run `tito tag` or imitate that commit
format; it will disrupt versioning and the release process.
