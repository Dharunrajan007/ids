"""Replay core: payload construction, pacing, and failure handling.

Pure stdlib + the project's frozen column lists, so the whole replay loop is
unit-testable with a fake `send` callable — no HTTP, no running API.

Data rule (binding): KDDTest+ is REPLAY INPUT ONLY here. Payloads carry
exactly the 40 M2 feature columns; `label`, `difficulty`, `is_attack` and
`category` never leave this process, and nothing in this package computes an
evaluation metric — the once-only locked evaluation belongs to M8.
"""

import random
import time
from dataclasses import dataclass, field

from src.preprocessing import FEATURE_COLUMNS

# Columns that exist on loaded NSL-KDD frames but must NEVER be transmitted.
FORBIDDEN_PAYLOAD_FIELDS = ("label", "difficulty", "is_attack", "category")

# How long to wait before retrying when the API is unreachable.
RECONNECT_WAIT_SECONDS = 2.0


class ApiUnreachable(Exception):
    """The request never reached the API (connection refused/reset).

    Safe to retry the same row — the server processed nothing.
    """


class RequestTimeout(Exception):
    """No response within the timeout. The server MAY have processed the
    request, so the row is counted as a timeout and skipped rather than
    retried — a retry could create a duplicate prediction in the feed."""


def build_payload(row):
    """One dataset row -> the /predict feature dict.

    Selects exactly FEATURE_COLUMNS (the M2 allow-list the API schema is
    generated from), converting numpy scalars to plain Python so the payload
    JSON-serializes. Anything else on the row — labels included — is simply
    never read.
    """
    payload = {}
    for name in FEATURE_COLUMNS:
        value = row[name]
        payload[name] = value.item() if hasattr(value, "item") else value
    return payload


def replay_payloads(frame, *, rows=None, shuffle=True, seed=42):
    """Yield payload dicts from a loaded NSL-KDD frame.

    shuffle defaults ON (seeded, so the demo is repeatable): KDDTest+ rows
    are grouped by collection order, and a sequential replay can show one
    attack type for minutes — a shuffled replay mixes normal traffic and
    attack categories the way the dashboard demo needs. Presentation
    ordering only; predictions are unaffected. `rows=None` replays the
    whole frame.
    """
    order = list(frame.index)
    if shuffle:
        random.Random(seed).shuffle(order)
    if rows is not None:
        order = order[:rows]
    for index in order:
        yield build_payload(frame.loc[index])


@dataclass
class ReplayStats:
    sent: int = 0            # requests that got any HTTP response
    ok: int = 0              # 200s
    attacks: int = 0         # 200s whose prediction was "attack"
    rejected: int = 0        # 422s (should not happen with real rows)
    server_errors: int = 0   # 5xx
    timeouts: int = 0
    connection_failures: int = 0  # unreachable episodes (row retried)
    elapsed: float = 0.0

    def rate(self):
        return self.sent / self.elapsed if self.elapsed > 0 else 0.0

    def summary(self):
        return (f"sent {self.sent} | ok {self.ok} | attacks observed "
                f"{self.attacks} | 422 {self.rejected} | 5xx "
                f"{self.server_errors} | timeouts {self.timeouts} | "
                f"reconnects {self.connection_failures} | "
                f"{self.elapsed:.1f}s @ {self.rate():.2f} flows/s")


def run_replay(payloads, send, *, rate=1.5, duration=None,
               sleep=time.sleep, clock=time.monotonic, log=print,
               progress_every=10):
    """Send payloads through `send` at `rate` flows/s until the iterator,
    the optional duration cap, or Ctrl+C ends the run. Returns ReplayStats.

    One request at a time, paced by absolute schedule (next slot += interval)
    so a fast API doesn't cause a burst and a slow response naturally slows
    the replay instead of stacking concurrent requests — the API is never
    flooded. `send`, `sleep`, `clock` and `log` are injectable for tests.

    `send(payload)` must return (status_code, body_dict) or raise
    ApiUnreachable / RequestTimeout.
    """
    interval = 1.0 / rate
    stats = ReplayStats()
    started = clock()
    next_at = started
    try:
        for payload in payloads:
            # Enforce the cap against the time this row WOULD be sent, so
            # the pacing sleep can't carry the replay past the duration.
            now = clock()
            scheduled = max(now, next_at)
            if duration is not None and scheduled - started >= duration:
                log(f"duration cap ({duration}s) reached")
                break
            if now < next_at:
                sleep(next_at - now)
            next_at = next_at + interval

            while True:  # retry the SAME row only while the API is down
                try:
                    status, body = send(payload)
                except ApiUnreachable:
                    stats.connection_failures += 1
                    log(f"API unreachable — retrying in "
                        f"{RECONNECT_WAIT_SECONDS:.0f}s (start it with: "
                        "python -m uvicorn api.main:app --port 8000)")
                    sleep(RECONNECT_WAIT_SECONDS)
                    continue
                except RequestTimeout:
                    stats.timeouts += 1
                    log("request timed out — skipping row (no retry: the "
                        "server may have processed it)")
                    status = None
                break

            if status is None:
                continue
            stats.sent += 1
            if status == 200:
                stats.ok += 1
                if body.get("prediction") == "attack":
                    stats.attacks += 1
            elif status == 422:
                stats.rejected += 1
                log(f"422 rejected (unexpected for dataset rows): {body}")
            else:
                stats.server_errors += 1
                log(f"HTTP {status} from API")

            if progress_every and stats.sent % progress_every == 0:
                stats.elapsed = clock() - started
                log(f"[{stats.sent}] {stats.summary()}")
    except KeyboardInterrupt:
        log("\ninterrupted — stopping cleanly")
    stats.elapsed = clock() - started
    return stats
