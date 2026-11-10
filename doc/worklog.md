# Shared Work Log

## Purpose and repository overview

This Python repository controls a SmarAct SmarPod six-degree-of-freedom
positioner carrying a probe-based confocal laser endomicroscopy (pCLE) probe.
It captures images from the pCLE viewer, sends them to a remote inference
server over TCP, and uses returned distance and orientation estimates for
visual servoing. It also includes labelled data collection, probe calibration,
manual motion tools, SDK examples, and image mosaicking.

## Collaboration agreement

- Both agents maintain this shared log in English on branch `rae`.
- Each agent records its own work with a stable agent identifier.
- Append an entry after each meaningful task, including documentation changes.
- Read the latest log before editing; preserve the other agent's entries and
  resolve concurrent edits by retaining both records.
- Record actual results, validation, limitations, and handoff items. Never claim
  another agent's work or mark planned work as completed.
- Use Europe/London dates and times; include the timezone when recording a time.
- Agent identifiers: `Codex (initial setup)` and a stable identifier chosen by
  the collaborating agent when it first contributes.
- Identifier rule (from 2026-11-07, approved by the project owner): sign every
  new entry as `<Agent> (<OS>)`, where `<Agent>` is `Codex` or `Claude Code`
  and `<OS>` is `Windows` or `macOS`, e.g. `Claude Code (Windows)` or
  `Codex (macOS)`. Use the OS the work was actually done on. Earlier entries
  keep their original identifiers and must not be rewritten.

## Entry template

Copy this template beneath the existing entries:

```markdown
### YYYY-MM-DD — Agent identifier — Task title

- Request / objective:
- Branch / base commit:
- Work completed:
- Files changed:
- Validation and results:
- Limitations / blockers:
- Next steps / handoff:
```

## Entries

### 2026-11-05 — Codex (initial setup) — Repository review and shared log setup

- Request / objective: Summarize the repository, check Git access, create `rae`
  from `yulin` if accessible, and create an English work log template in `doc/`
  for two agents to record their respective work.
- Branch / base commit: `rae`, created from `yulin` at
  `320e7b7948ec7c6f06b529062a234299d526c85c`.
- Work completed: Reviewed the repository guides, file layout, client code,
  and shared networking helpers; summarized the project above; checked remote
  access; created the local branch and this shared log with collaboration rules.
- Files changed: `doc/worklog.md` (new).
- Validation and results: The working tree was initially clean. `git ls-remote
  origin` succeeded for `https://github.com/Yulin0217/pri.git`; local `yulin`
  matched the remote branch. `git push --dry-run origin yulin:refs/heads/rae`
  succeeded and reported a new branch, verifying push preflight access without
  changing the remote. Local branch creation succeeded.
- Limitations / blockers: No hardware scripts were executed for this
  documentation-only task. A dry run does not guarantee every server-side
  hook will accept an actual push. No commit or remote push has been made.
- Next steps / handoff: The collaborating agent should read this file and
  append its own entries using a stable identifier. Both agents should continue
  recording their work in English and preserve each other's entries.

### 2026-11-05 — Codex (initial setup) — Refresh yulin

- Request / objective: Pull the latest `yulin` branch from the remote.
- Branch / base commit: Local `yulin` advanced from `320e7b7` to `cd79ba9`
  (`Refactor SmarPod client into a portable Python package`).
- Work completed: Fetched `origin/yulin`, verified that the update was a
  fast-forward, and updated local `yulin` to match it.
- Files changed: `doc/worklog.md` on the current `rae` working tree.
- Validation and results: Fetch and local branch update succeeded; the current
  branch remains `rae`, and the existing work log was preserved.
- Limitations / blockers: `rae` has not been merged or rebased onto the updated
  `yulin`; this log remains uncommitted.
- Next steps / handoff: Use the refreshed `yulin` for subsequent work as needed.

### 2026-11-05 — Codex (initial setup) — Create Conda development environment

- Request / objective: Create the Conda environment required by the repository.
- Branch / base commit: Switched to `yulin` at `cd79ba9`, which contains the
  environment recipe and installable package; retained the existing work log.
- Work completed: Installed Miniconda for macOS arm64 at
  `/Users/happy/miniconda3`; created `smarpod-pcle` from `environment.yml`
  with Python 3.12.16 and an editable installation of `.[dev]`.
  Disabled external Conda plugins for creation to bypass the default-channel
  ToS check; package downloads used the recipe's conda-forge channel.
- Files changed: `doc/worklog.md`; generated ignored build/install artifacts.
- Validation and results: Default doctor passed; all 44 tests passed; Ruff and
  pip dependency checks passed; source distribution and wheel built successfully.
- Limitations / blockers: No hardware, screen capture, or remote inference
  validation was performed. Current branch is `yulin`; `rae` was not rebased.
  Shell startup files were not modified. Log changes remain uncommitted.
- Next steps / handoff: Activate with
  `source /Users/happy/miniconda3/etc/profile.d/conda.sh` followed by
  `conda activate smarpod-pcle`. The editable installation points to this
  checkout, so keep a branch containing the package checked out when using it.

### 2026-11-05 — Codex (initial setup) — Force-align rae with latest yulin

- Request / objective: Overwrite local `rae` to match the latest remote `yulin`.
- Branch / base commit: `rae` now points to
  `a2be938554d81d755de643028e0f6c73293aa3b7`, identical to `origin/yulin`.
- Work completed: Fetched remote `yulin`, force-updated local `rae`, and switched
  to `rae`; its upstream is `origin/yulin`.
- Files changed: `doc/worklog.md` (appended this entry).
- Validation and results: Verified both branch commit hashes match; no tracked
  working-tree changes remain. The untracked `doc/` work log is preserved.
- Limitations / blockers: No remote branch was changed or pushed.
- Next steps / handoff: Continue work on `rae` and append each agent's actions here.

### 2026-11-05 — Claude Code (code & review) — Join project and baseline check

- Request / objective: Join as the agent responsible for code changes and
  review feedback; co-maintain this shared log with Codex.
- Branch / base commit: `rae` at `a2be938` (identical to `origin/yulin`).
- Work completed: Read this log and the tracked `docs/worklog.md`; ran the
  offline baseline checks. Per owner instruction, this file (`doc/worklog.md`)
  is the shared log for both agents; my initial entry briefly added to
  `docs/worklog.md` was reverted.
- Files changed: `doc/worklog.md` (appended this entry).
- Validation and results: In `smarpod-pcle`, `ruff check src tests` passed;
  `pytest` passed (47 tests, 60 subtests). No hardware, capture, or inference
  server accessed.
- Limitations / blockers: `doc/` is untracked; the tracked `docs/worklog.md`
  (from `yulin`) remains with its own history and is not updated by this log.
- Next steps / handoff: Awaiting the next code task; I will record code
  changes and review feedback here.

### 2026-11-05 — Claude Code (code & review) — Commit and publish shared log

- Request / objective: Commit the shared log and push `rae` to the remote.
- Branch / base commit: `rae` at `a2be938`.
- Work completed: Committed `doc/worklog.md` (all entries above, both agents)
  and pushed `rae` to new remote branch `origin/rae`; set local `rae` upstream
  to `origin/rae` (previously `origin/yulin`).
- Files changed: `doc/worklog.md`.
- Validation and results: Recorded in the push output; see next entry if any
  issue arises.
- Limitations / blockers: None.
- Next steps / handoff: Both agents pull/push `origin/rae`; `yulin` untouched.

### 2026-11-07 — Claude Code (Windows) — Join from Windows and set identifier rule

- Request / objective: Verify GitHub access from the Windows machine, read this
  log, switch to `rae`, and add an owner-approved agent identifier rule.
- Branch / base commit: `rae` at `2915826` (matches `origin/rae`).
- Work completed: Confirmed fetch/pull from `origin`; switched local checkout
  from `main` to `rae` tracking `origin/rae`; added the `<Agent> (<OS>)`
  identifier rule to the collaboration agreement.
- Files changed: `doc/worklog.md`.
- Validation and results: `git fetch`/`git pull` succeeded. `git push
  --dry-run` to a new ref succeeded, so push credentials work; no remote ref
  was created. No code, tests, or hardware were run.
- Limitations / blockers: Git author identity (`user.name`/`user.email`) is
  not configured on this Windows machine, so this change cannot be committed
  yet.
- Next steps / handoff: Commit and push once the identity is set. Other agents
  should use the new identifier format from their next entry.

### 2026-11-10 — Claude Code (Windows) — Detect and open SmarPod controller

- Request / objective: Detect the newly connected robot from the Windows
  machine and test a connection.
- Branch / base commit: `rae` at `8d88b3a`.
- Work completed: Found the FTDI USB serial device (COM5). In conda env
  `smarpod-pcle`, `smaract.smarpod` loads (API 1.9.0, DLL 1.9.7) only when the
  env is activated (e.g. `conda run -n smarpod-pcle`); calling the env's
  `python.exe` directly fails with `cannot load library 'SmarPod.dll'` because
  `Library\bin` is not on PATH. `FindSystems()` returned `usb:id:137043805`.
  A read-only probe script (outside the repo) ran `Open(10001, locator)`,
  queried status, and `Close` without any motion command.
- Files changed: `doc/worklog.md`.
- Validation and results: `Open` succeeded; `IsReferenced` = 0 (not
  referenced); `GetMoveStatus` = 0; `GetPose` returned error 550, presumably
  because the stage is not referenced. No calibration, referencing, or motion.
- Limitations / blockers: Running `SmarPod_init` will reference the stage,
  which moves it physically. `config/example.toml` uses locator `usb:ix:0`;
  `usb:id:137043805` was not tested through the project config. The env's
  editable `smarpod_pcle` install points to another checkout
  (`C:\Users\Rayan\Documents\Codex\...\work\pri`), not `C:\Users\Rayan\pri`.
  Correction to the 2026-11-07 entry: the Git identity is now set, and that
  entry was committed and pushed.
- Next steps / handoff: Before any motion, the owner should confirm the probe
  and sample are clear and then reference the stage. Decide which checkout the
  `smarpod-pcle` env should use.

### 2026-11-10 — Claude Code (Windows) — First motion test

- Request / objective: Owner asked to make the robot move as a test.
- Branch / base commit: `rae` at `ea4096d`.
- Work completed: With a script outside the repo (env `smarpod-pcle`, via
  `conda run`), opened `usb:id:137043805` as model 10001, enabled sensors,
  ran `FindReferenceMarks` (no calibration), set speed to 1 mm/s, moved
  +0.5 mm in X and back. `Stop` and `Close` ran in a `finally` block.
- Files changed: `doc/worklog.md`.
- Validation and results: Referencing took 4.4 s; `IsReferenced` = 1.
  Pose (X/Y/Z mm; Rx/Ry/Rz deg):
  start -1.0785/1.8935/-0.0184; 2.0280/1.1390/2.0352,
  after +X -0.5784/1.8933/-0.0185,
  back -1.0781/1.8934/-0.0188. The X step was 0.5001 mm, and the return
  error was below 0.5 µm in X and Y and below 0.5 µm in Z. No errors.
- Limitations / blockers: Only X translation was tested. The stage is now
  referenced but not at the zero pose, and the rotations are about 1-2 deg.
- Next steps / handoff: Project workflows can now use the referenced stage.
  Confirm the intended home pose before running `SmarPod_init`-based tools.

### 2026-11-10 — Claude Code (Windows) — Move stage to zero pose

- Request / objective: Owner asked to return the robot to the zero pose.
- Branch / base commit: `rae` at `086593f`.
- Work completed: With a script outside the repo, checked that the stage was
  still referenced, set speed to 1 mm/s, checked that the zero pose was
  reachable, and moved to (0, 0, 0 mm; 0, 0, 0 deg). Stop/Close in `finally`.
- Files changed: `doc/worklog.md`.
- Validation and results: Before: X/Y/Z -1.0787/1.8934/-0.0183 mm,
  Rx/Ry/Rz 2.0280/1.1393/2.0348 deg. After: every axis read 0.0000 (mm, deg).
  No errors.
- Limitations / blockers: The default pivot was used (pivot mode not set),
  unlike `SmarPod_init`, which sets a relative pivot.
- Next steps / handoff: The stage is referenced and at the zero pose.

### 2026-11-10 — Claude Code (Windows) — Repeat X motion test from zero

- Request / objective: Owner asked to move the robot again.
- Branch / base commit: `rae` at `9980ae7`.
- Work completed: Reran the earlier out-of-repo test script from the zero
  pose: +0.5 mm in X and back at 1 mm/s (stage already referenced, so no
  referencing). Stop/Close in `finally`.
- Files changed: `doc/worklog.md`.
- Validation and results: After +X, X = 0.4990 mm. Back: X/Y/Z
  0.0005/-0.0003/0.0001 mm, Rx/Ry/Rz -0.0004/0.0026/-0.0009 deg. No errors.
- Limitations / blockers: None.
- Next steps / handoff: The stage is referenced and at the zero pose (within
  about 0.5 µm and 0.003 deg).
