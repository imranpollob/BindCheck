# D1P-17 — Q3 monitor audit and bounded runner repair

Date: 27 October 2026  
Task: D1P-17 monitor subtask  
Task status: **DONE**  
D1P-14D Q3: **UNKNOWN (unchanged)**  
D1 security verdict: **UNKNOWN**

## 1. Outcome

D1P-17 audited the immutable D1P-14D Q3 record without rerunning that query
and repaired the prospective macOS process runner in a new namespace. The old
record supports four ordered facts, not a causal diagnosis:

1. libproc reported root PID `54891` absent after 4,196 earlier samples;
2. `wait(timeout=0.25)` did not confirm process exit;
3. the attempted process-group `SIGKILL` failed with `EPERM`, recorded as
   `Operation not permitted`; and
4. a following `wait()` reaped the child with return code `-9`.

The old runner recorded neither a successful process-group kill nor a direct
kill. Return code `-9` identifies termination by `SIGKILL`; by itself it does
not identify who or what sent the signal. Root-process disappearance, cleanup
access failure, and confirmed process exit are therefore distinct events.
The preserved empty stdout/stderr files contain no SAT/UNSAT answer. D1P-14D
Q3 remains `UNKNOWN`.

The repaired runner records those categories and their chronology separately.
It passed the five required harmless lifecycle cases and two focused failure-
classification regressions. All launched root processes had an exit confirmed
by `poll()` or `wait()`, and both spawned-child cases left no surviving child.

## 2. Immutable D1P-14D chronology

The copied source record is SHA-256
`0d5c759cb2eb4be242207642c061610ecb356d361791051cd3fabea49dea64a8`.
Its exact input was Q3 SHA-256
`922df98e7d6fd04fb24628462039199515257aab78c08bc3b6ee02ea617b141d`.

| Phase | Recorded fact | What it does not establish |
|---|---|---|
| last successful sample | PID `54891`, 369,033,216 B RSS; peak 1,657,716,736 B | continued monitor access |
| root observation | `root_present=false` | process exit |
| bounded wait | timed out | exit or signal cause |
| group cleanup | `PermissionError: [Errno 1] Operation not permitted` | a successful runner kill |
| reap | return code `-9` | source of `SIGKILL` |

The call ended after 229.747027 seconds, below its 300-second bound, with no
memory-cutoff observation and no solver text. It is inaccurate to describe
`-9` alone as a memory kill, runner kill, solver crash, or normal exit.

## 3. Repair

`src/bindcheck_d1/process_runner_d1p17.py` makes the monitor advisory and uses
`Popen.poll()`/`wait()` as the only exit confirmation. It records:

- root disappearance as an observation;
- libproc or PID-probe access denial as `MONITOR_ACCESS_FAILURE`;
- bounded exit-confirmation attempts independently;
- process-group and direct cleanup attempts, including `EPERM`;
- whether the runner actually sent `SIGKILL`; and
- the confirmed return code and a qualified attribution string.

After a confirmed early root exit it also attempts bounded cleanup of the
residual process group, covering a child that has already been reparented and
is no longer discoverable through the former root.

## 4. Harmless lifecycle tests

| Case | Observed status | Seconds | Confirmed exit | Additional check |
|---|---|---:|---|---|
| normal exit | `COMPLETED`, exit 0 | 0.029603 | `poll` | stdout/log record present |
| timeout | `TIMEOUT`, exit -9 | 0.265106 | wait after group cleanup | runner kill recorded |
| memory cutoff | `MEMORY_CUTOFF`, exit -9 | 0.060310 | wait after group cleanup | 77,594,624 B observed over 48 MiB cutoff |
| child spawn | `TIMEOUT`, exit -9 | 0.355342 | wait after group cleanup | peak process count 2; child absent afterward |
| early root exit | `COMPLETED`, exit 0 | 0.067916 | `poll` | residual child absent afterward |
| synthetic access denial | `MONITOR_ACCESS_FAILURE` | 0.003368 | wait after cleanup | access failure distinct from root loss |
| synthetic missing root | `ROOT_MONITOR_LOSS` | 0.506348 | wait after cleanup | root loss distinct from exit confirmation |

These are runner regressions, not evidence about cvc5 reliability or the cause
of D1P-14D Q3.

## 5. Prospective Q3 observation

The frozen D1P-17 T-OVF Q3 diagnostic later encountered a similar, separately
recorded sequence after 231.859236 seconds: root absent; no confirmed exit in
0.5 seconds; zero-signal PID probe `EXISTS`; cleanup requested; process-group
cleanup failed with `EPERM`; then `wait()` confirmed `-9`. No successful
runner kill was recorded, so the signal source is again unidentified. The
call is `ROOT_MONITOR_LOSS / UNKNOWN`. Recurrence does not establish a cause.

## 6. Commands and evidence

Commands executed from the task worktree included:

```text
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py prepare
PYTHONPATH=src python3 scripts/d1p_17_backend_study.py monitor-tests
```

Evidence:

- audit: `results/raw/D1P-17/d1p14d-q3-chronology-audit.json`;
- exact copied predecessor records: `results/raw/D1P-17/inputs/`;
- lifecycle ledger and per-call chronology:
  `results/raw/D1P-17/monitor-tests.json` and `monitor-tests/calls/`;
- prospective primary ledger: `results/raw/D1P-17/primary-ledger.json`;
- repaired runner: `src/bindcheck_d1/process_runner_d1p17.py`, SHA-256
  `894475d3346990614c1f2c5a526d1ddcdf609eb281973491b2a43bd3178ec0d2`.

Host: macOS 27.0.1 arm64; Python 3.13.9. No D1P-14B/C/D report, raw file,
query, or tracked artifact was edited.

## 7. Limits

The repair improves classification and cleanup evidence; it does not make
libproc a hard resource limit, identify an external signal source, explain the
two Q3 root-loss events, or change either Q3 result. The 50 ms RSS sampler can
overshoot and can lose visibility before process exit.

