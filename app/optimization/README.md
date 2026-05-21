# Optimization Prototype Boundary

`app/optimization/algorithms.py` is an isolated prototype asset for `M5 / P3-05`.

It is not currently part of the production runtime:

- no API router imports it
- no service imports it
- no scheduler or task runner imports it
- no ORM model or migration depends on it

Rules before reuse:

- add a stable adapter contract in `app/services/optimization_service.py`
- add focused tests for sampling, duplicate handling, termination, and best-trial selection
- decide whether Bayesian optimization belongs in `M5 v1` or a later enhancement
- keep current architecture and class diagrams limited to implemented runtime paths

See `docs/milestones/m5/M5_P3-05_RESIDUE_DECISIONS.md` for the current disposition.
