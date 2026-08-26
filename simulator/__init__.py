"""Milestone 7 — traffic replay simulator (ADR-006).

Replays KDDTest+ rows through the SAME HTTP prediction path everything else
uses: POST /predict on the running FastAPI service. This is simulated traffic
replay for the demo — NOT live network capture, and NOT model evaluation.
The simulator never imports the model, never sees a metric, and never sends
a ground-truth label anywhere. Run from the project root:

    python -m simulator.run
"""
