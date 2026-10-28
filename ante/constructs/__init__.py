"""Constructs: expertise frozen read-only — consultable, unable to learn.

Two uses:

- **frozen reviewers** (``frozen.py``): reviewer profiles pinned by hash in
  ``frozen.json``. They are the evaluator the improver cannot touch: ``ante
  develop`` refuses any change to them and ``ante learn`` cannot write to them.
- **decision snapshots** (``snapshot.py``): when ``decide`` runs, what was known —
  the parents, every claim visible with its status and origin, the dated
  expectations — is frozen inside the record. ``learn reconcile`` and
  ``calibrate`` compare outcomes only against that snapshot, so later knowledge
  cannot rewrite what the decision was based on (Marco I.10).

In decision artefacts these appear as ``frozen_reviewer`` and ``snapshot``.
"""
