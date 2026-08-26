"""Milestone 7 runner: replay KDDTest+ flows through the live prediction API.

Usage (from the project root, with the API running on :8000):
    python -m simulator.run                     # demo defaults: 300 rows @ 1.5/s
    python -m simulator.run --rate 4 --rows 100
    python -m simulator.run --sequential        # dataset order instead of mix

This is SIMULATED TRAFFIC REPLAY through the same prediction API path — not
live network capture, and not model evaluation. Ground-truth labels never
leave this process and no metric is computed (see simulator/replay.py).
"""

import argparse
import time

from simulator.client import DEFAULT_API_URL, check_health, make_sender
from simulator.replay import replay_payloads, run_replay
from src.data_loader import load_nslkdd


def wait_for_api(api_url, timeout):
    while True:
        health = check_health(api_url, timeout)
        if health and health.get("model_loaded"):
            print(f"API online — model {health.get('model_version', '?')}")
            return
        print(f"API not reachable at {api_url} — retrying in 2s "
              "(start it with: python -m uvicorn api.main:app --port 8000)")
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API_URL,
                        help="prediction API base URL")
    parser.add_argument("--rate", type=float, default=1.5,
                        help="flows per second (demo pace, not a load test)")
    parser.add_argument("--rows", type=int, default=300,
                        help="how many flows to replay (0 = the whole file)")
    parser.add_argument("--duration", type=float, default=None,
                        help="optional wall-clock cap in seconds")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="per-request timeout in seconds")
    parser.add_argument("--sequential", action="store_true",
                        help="replay in dataset order instead of the seeded "
                             "shuffle (the shuffle only mixes attack types "
                             "for a livelier demo; predictions are "
                             "unaffected)")
    parser.add_argument("--seed", type=int, default=42,
                        help="shuffle seed (presentation order only)")
    args = parser.parse_args()
    if args.rate <= 0:
        parser.error("--rate must be positive")

    frame = load_nslkdd("test")  # replay input ONLY — labels never leave
    rows = None if args.rows == 0 else args.rows
    print(f"replaying {rows or len(frame)} of {len(frame):,} KDDTest+ flows "
          f"@ {args.rate:g}/s -> {args.api}/predict "
          f"({'sequential' if args.sequential else f'shuffled seed={args.seed}'})")

    wait_for_api(args.api, args.timeout)
    payloads = replay_payloads(frame, rows=rows,
                               shuffle=not args.sequential, seed=args.seed)
    stats = run_replay(payloads, make_sender(args.api, args.timeout),
                       rate=args.rate, duration=args.duration)
    print(f"\ndone — {stats.summary()}")
    print("watch it live: http://localhost:5173 (dashboard polls every 2s)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C during startup/wait_for_api (the replay loop handles its
        # own) — exit quietly instead of dumping a traceback mid-demo.
        print("\nstopped")
