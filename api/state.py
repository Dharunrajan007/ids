"""Bounded in-memory prediction history and statistics (ADR-008 — no database).

Sizing decisions (documented, all bounded so memory cannot grow with uptime):
- HISTORY_LIMIT = 1000 records. The dashboard's live feed asks for at most
  MAX_RECENT_LIMIT=500, and at the simulator's demo pace (~1 flow/s) 1000
  records is ~17 minutes of full-detail lookback. Each record holds the 40
  submitted features (~1 KB), so the deque tops out around 1 MB.
- TIMELINE_MINUTES = 60. The stats chart shows per-minute normal/attack
  counts; an hour of bars is more than the demo needs, at ~60 tiny entries.
- Lifetime counters (total/normal/attack/by-type) are plain integers, so
  /stats totals stay correct even after old records fall off the deque.

History intentionally resets when the API restarts (frozen contract note).
A threading.Lock guards every mutation/read: FastAPI runs sync endpoints in
a thread pool, so concurrent requests would otherwise race.
"""

import threading
from collections import Counter, OrderedDict, deque

from api.schemas import ATTACK_TYPES

HISTORY_LIMIT = 1000
TIMELINE_MINUTES = 60


class PredictionHistory:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        """Fresh state — used at startup and between tests."""
        with getattr(self, "_lock", threading.Lock()):
            self._records = deque(maxlen=HISTORY_LIMIT)
            self._total = 0
            self._normal = 0
            self._attacks_by_type = Counter()
            # minute ("HH:MM" UTC) -> [normal_count, attack_count],
            # insertion-ordered so trimming drops the oldest minute.
            self._timeline = OrderedDict()

    def add(self, record: dict):
        """Store one /predict result. record = response fields + features."""
        with self._lock:
            self._records.append(record)
            self._total += 1
            if record["prediction"] == "normal":
                self._normal += 1
            else:
                self._attacks_by_type[record["attack_type"]] += 1
            # Keyed by full "YYYY-MM-DDTHH:MM" (displayed as "HH:MM") so a
            # long-lived server never merges today's 10:14 into yesterday's
            # still-resident 10:14 bucket — audit finding on the HH:MM-only
            # key. Eviction stays count-based over the last 60 distinct
            # minutes seen.
            minute = record["timestamp"][:16]
            if minute not in self._timeline:
                self._timeline[minute] = [0, 0]
                while len(self._timeline) > TIMELINE_MINUTES:
                    self._timeline.popitem(last=False)
            self._timeline[minute][0 if record["prediction"] == "normal"
                                   else 1] += 1

    def recent(self, limit: int) -> list:
        """Newest first."""
        with self._lock:
            return list(self._records)[::-1][:limit]

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_flows": self._total,
                "normal_count": self._normal,
                "attack_count": self._total - self._normal,
                "attacks_by_type": {
                    kind: self._attacks_by_type.get(kind, 0)
                    for kind in ATTACK_TYPES
                },
                "traffic_timeline": [
                    {"minute": minute[11:], "normal": counts[0],
                     "attack": counts[1]}
                    for minute, counts in self._timeline.items()
                ],
            }
