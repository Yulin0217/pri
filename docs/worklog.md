# Shared Agent Worklog

## Maintenance requirements

This directory and worklog are maintained jointly by the primary agent and all
other agents working on this project. These requirements were requested by the
project owner on 5 November 2026.

1. **Use English.** Write documentation, worklog entries, and updates to these
   requirements in English.
2. **Read before working.** Read this file and the relevant documents in `docs/`
   before making changes. Follow the current handoff notes and coordinate with
   other agents to avoid conflicting edits.
3. **Record your own work.** Every participating agent must add an entry for its
   completed work or handoff. Use the actual agent name; do not take credit for
   another agent's work. The primary agent records integration and commits.
4. **Describe concrete changes.** Include the purpose, affected files or areas,
   decisions that matter to maintainers, and any changes in behavior. Use
   repository-relative paths so entries remain useful on another computer.
5. **Report evidence accurately.** Record checks actually performed and their
   results. Distinguish offline tests, mocked hardware, and real hardware
   validation. State when a check was not run; do not present planned work as
   completed or imply that another agent's checks were your own.
6. **Leave a clear handoff.** List unresolved issues, dependencies, limitations,
   and next actions. Use `None` when there are no outstanding items for the entry.
7. **Preserve history.** Append entries in completion order. Do not delete or
   silently rewrite another agent's entry. Add a dated correction when necessary.
   Coordinate structural edits to this file with the primary agent; concurrent
   contributors should append only their own complete entries.
8. **Keep documentation current.** When changing file names, commands,
   configuration, interfaces, or behavior, update the affected files in `docs/`
   and their README links. The worklog supplements those guides; it does not
   replace them.
9. **Keep entries concise and safe to share.** Record meaningful outcomes rather
   than full transcripts or tool output. Do not include credentials, private
   machine configuration, or captured sample data.
10. **Use the project owner's time zone.** Date entries in `Europe/London`; include
    a time and offset only when useful. Mark retrospective entries explicitly
    and record only work supported by the conversation or repository history.

## Entry format

```markdown
### YYYY-MM-DD — Agent name — Short task title

- Scope: The task or problem addressed.
- Changes: What changed and the relevant repository-relative paths.
- Validation: Checks actually performed, results, and validation boundaries.
- Handoff: Outstanding work, limitations, or `None`.
- Commit: Commit identifier if already known, otherwise `Pending` or `Not applicable`.
```

## Work entries

### 2026-11-05 — /root — Establish shared documentation requirements

- Scope: Implement the owner's request for a jointly maintained English worklog.
- Changes: Created `docs/worklog.md` with collaboration requirements and an entry
  template; instructed contributing agents to record their own work here.
- Validation: Confirmed that `docs/` already exists. This entry records a
  documentation change; no hardware operation was performed.
- Handoff: Contributors will append their naming, comments, and documentation
  work. The primary agent will finish integration checks and commit the changes.
- Commit: Pending.

### 2026-11-05 — /root/client_refactor — Explain control and transport invariants

- Scope: Add key English comments after the primary agent's module renaming.
- Changes: Updated `src/smarpod_pcle/applications/visual_servo_client.py`,
  `src/smarpod_pcle/applications/spiral_stream_demo.py`,
  `src/smarpod_pcle/robot_control.py`, `src/smarpod_pcle/tcp_protocol.py`, and
  `src/smarpod_pcle/screen_capture.py`. Documented physical units, whole-reply
  queueing, signal lifecycle, main-thread robot ownership, lazy SDK loading,
  cleanup order, trusted pickle framing, per-read socket timeouts, and BGRA
  conversion. These edits changed comments/docstrings only; no renaming or
  runtime behavior was changed by this agent in this assignment.
- Validation: Compared parsed AST fingerprints for all five files before and
  after the edits, excluding docstrings; executable ASTs matched. No new tests
  were added or run for this documentation-only assignment. No hardware access
  was performed.
- Handoff: The primary agent owns integration checks and the pending commit.
  No outstanding issues in this contribution.
- Commit: Pending.

### 2026-11-05 — /root/legacy_refactor — Explain collection and mosaicking code

- Scope: Clarify key algorithms and lifecycle decisions after the primary agent's
  module renames, without changing behavior.
- Changes: Added English comments and docstrings in
  `src/smarpod_pcle/data_collection/{collection_helpers,distance_sweep,orientation_sweep,spiral_capture}.py`
  and `src/smarpod_pcle/mosaicking/{mosaic_canvas,scan_runner,direct_mosaic,regression_mosaic}.py`.
  Explained manual focus references, units and axis signs, recording labels only
  after successful image writes, and stopping without homing on errors. Clarified
  regression reference-frame priming, permanent fallback, displacement accumulation,
  canvas clipping, coordinate mapping, and overlap averaging.
- Validation: Compared parsed ASTs before and after editing, excluding docstrings;
  executable code was unchanged across all 10 modules in the two directories.
  `ruff check src/smarpod_pcle/data_collection src/smarpod_pcle/mosaicking` passed
  in the `smarpod-pcle` conda environment. No tests were added or run for these
  comment-only edits, and no hardware was accessed.
- Handoff: The primary agent will integrate and commit these documentation-only
  code changes. No unresolved issue in this scope.
- Commit: Pending.

### 2026-11-05 — /root/portability_audit — Deployment and naming documentation (retrospective)

- Scope: Audit cross-computer requirements, document deployment/protocol behavior,
  and align English guides with the descriptive package and command names.
- Changes: Authored `docs/portability.md` and `docs/protocol.md` using primary
  SmarAct, MSS, Apple, and Python sources. Updated `README.md`,
  `docs/development.md`, `docs/data-collection.md`, and `summer_school/README.md`;
  added `docs/project-layout.md` with file responsibilities, command options,
  supported aliases, root-script mappings, and Python import migration limits.
  Linked this worklog from the README and added the read/update instruction to
  the development guide. Kept offline Mac development separate from control-PC
  requirements and preserved operational caveats.
- Validation: Read-only comparison of documentation against configuration and
  workflow implementations; checked all 70 local Markdown links and anchors
  across eight documents successfully after adding the worklog links. Earlier
  vendor research established public Windows/Linux SDK support without claiming
  Mac hardware support. No unit tests, robot operations, screen capture, or
  inference-server connections were performed by this agent.
- Handoff: The primary agent owns final integration checks and the commit.
  Actual SDK/controller/capture/server validation remains for the control setup.
- Commit: Pending.

### 2026-11-05 — /root/portability_audit — Consolidate maintained documentation

- Scope: Remove redundant original documentation and improve the remaining guides.
- Changes: Deleted `summer_school/README.md`, whose redirect and workflow mapping
  duplicated `docs/data-collection.md` and `docs/project-layout.md`; removed its
  Markdown inclusion pattern from `MANIFEST.in` while retaining all Python
  adapters. Added a complete documentation index to `README.md`, consolidated
  repeated CLI/options/alias guidance into README references, and simplified the
  portability installation steps. Corrected `docs/protocol.md` to state that
  receive timeouts apply per socket read, not to a whole-message deadline.
  Preserved operational caveats, compatibility information, and prior worklog history.
- Validation: Audited the Markdown inventory and stale-name references; validated
  69 local links/anchors across the seven remaining documents. Confirmed no active
  guide references the deleted README and the manifest retains canonical docs and
  legacy Python adapters. Scoped `git diff --check` passed. No unit tests or real
  hardware/capture/server checks were run for this documentation-only cleanup.
- Handoff: The primary agent owns integration, package checks, and the pending
  commit. No outstanding issue in the documentation cleanup.
- Commit: Pending.

### 2026-11-05 — /root/client_refactor — Review renamed entry points

- Scope: Final read-only review of command routing, aliases, historical script
  adapters, and internal imports after the naming migration.
- Changes: No code changes. Reviewed `src/smarpod_pcle/cli.py`, root compatibility
  wrappers, `tests/test_cli_compatibility.py`, and the migration guidance in
  `docs/development.md` and `docs/project-layout.md`. Found no actionable routing
  or import defect. Former internal package paths are intentionally unsupported;
  old script paths use the CLI or `SMARPOD_PCLE_CONFIG` for global configuration,
  as documented.
- Validation: The three tests in `tests/test_cli_compatibility.py` passed in the
  project conda environment, covering alias dispatch, help without workflow
  loading, and argument forwarding from `apps/client.py`. Searched maintained
  imports for stale package names and inspected all retained workflow wrappers.
  No hardware, screen capture, or external network access was performed.
- Handoff: None.
- Commit: Pending.

### 2026-11-05 — /root — Integrate descriptive names and shared documentation

- Scope: Complete the owner's requests for clearer folder/file/command names,
  key English code comments, a jointly maintained worklog, and removal of
  redundant documentation.
- Changes: Renamed the maintained package into `applications/`,
  `data_collection/`, `interactive_tools/`, `scan_experiments/`, and
  `sdk_examples/`, with descriptive workflow and shared-module filenames.
  Updated imports, test filenames, and root adapters. Added primary commands
  `servo-client`, `spiral-demo`, and `sdk-pose-sequence`, preserving the old
  command aliases and original root script paths. Kept existing TOML keys,
  motion algorithms, network payloads, and output formats unchanged. Added
  comments to configuration/output/jogging boundaries and corrected the XY
  cross-scan description. Integrated the other agents' comments, layout guide,
  documentation cleanup, and shared worklog entries. The deleted
  `summer_school/README.md` was a duplicate redirect; collection instructions
  remain in `docs/data-collection.md`.
- Validation: Ran Ruff successfully; the full offline suite passed with 47 tests
  and 60 subtests. The example-config doctor and `pip check` passed. Built both
  source and wheel distributions. Installed the wheel into a temporary directory
  outside the checkout, imported every command module, checked all primary and
  alias help commands, and ran the default doctor successfully. Verified that
  the wheel omits the old package tree and the source archive includes
  `docs/worklog.md`/`docs/project-layout.md` but not the deleted duplicate guide.
  These checks used offline code or mocked hardware; no controller, screen
  capture, or inference service was accessed.
- Handoff: No outstanding software issue found in this scope. Real SDK,
  controller, image capture, and inference-service acceptance remain separate
  control-computer checks. Future contributors must follow this worklog's
  maintenance requirements and update the canonical guides when behavior changes.
- Commit: Pending at entry time; this entry is included with the naming and
  documentation changes in the same commit.

### 2026-11-10 — /root — Review mosaic alternatives

- Scope: Inspect the existing spiral mosaic and research other scanning and stitching forms.
- Changes: Added `docs/mosaic-alternatives.md` with source mappings, trajectory comparisons, registration alternatives, research links, and a proposed raster-versus-spiral experiment. No runtime behavior changed.
- Validation: Read the canonical spiral, canvas, runner, regression and grid implementations and checked external research/tool sources. No hardware or runtime tests were run for this documentation-only task.
- Handoff: Alternative trajectories and image registration are proposals, not implemented features; physical coverage requires optical calibration.
- Commit: Pending.

### 2026-11-10 — /root — Implement independent alternative mosaic scans

- Scope: Correct the earlier documentation-only interpretation and provide runnable alternatives to spiral scanning.
- Changes: Removed `docs/mosaic-alternatives.md`. Added bounded serpentine, raster (including sampled return moves), and concentric-ring generators, separate package/CLI/script entries, optional dry-run JSON, and shared runner trajectory metadata. Preserved existing spiral defaults. Added usage documentation and tests.
- Validation: With this checkout on PYTHONPATH and a workspace temporary directory, 27 related tests and 47 subtests passed. Ruff passed for src, tests and mosaicking. Initial checks exposed the installed-package path, temporary-directory permissions, and floating-point spacing issues; rerouted checks and corrected spacing rounding/unit conversion. Full-suite runs stalled and were interrupted; no full-suite success is claimed. No actual hardware, capture or server validation.
- Handoff: Install this checkout on the control computer and calibrate overlap before hardware commissioning. Independent scripts use the shared backend intentionally.
- Commit: Pending.
