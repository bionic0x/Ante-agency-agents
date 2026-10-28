"""Apophenia guard: a pattern is proposed only if it beats chance, after counting how many were tried.

Every candidate pattern compares the rate of an outcome between decisions that
have a feature and decisions that do not. The guard:

- requires a minimum number of decisions on each side;
- computes a two-sided permutation p-value with a fixed seed (reproducible);
- adjusts it for the number of features tested (Bonferroni: the more patterns
  one looks for, the more one finds by chance);
- reports how many were tested, including the ones that failed.

It does not claim causation. A pattern that passes is a proposal for a human,
never a rule the system adopts by itself.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Verdict:
    feature: str
    with_feature: int
    without_feature: int
    rate_with: float
    rate_without: float
    difference: float
    p_value: float
    p_adjusted: float
    passes: bool
    reason: str

    def as_dict(self) -> dict:
        return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


def _rate(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def permutation_p(with_values: list[int], without_values: list[int], seed: int, rounds: int) -> float:
    observed = abs(_rate(with_values) - _rate(without_values))
    pooled = with_values + without_values
    size = len(with_values)
    rng = random.Random(seed)
    extreme = 0
    for _ in range(rounds):
        rng.shuffle(pooled)
        if abs(_rate(pooled[:size]) - _rate(pooled[size:])) >= observed - 1e-12:
            extreme += 1
    return (extreme + 1) / (rounds + 1)


def guard(samples: list[tuple[set[str], int]], features: list[str], seed: int = 20261028,
          rounds: int = 2000, alpha: float = 0.05, min_group: int = 3) -> tuple[list[Verdict], int]:
    """``samples``: (features present, outcome 0/1) per decision. Returns verdicts and the number tested."""
    tested = [f for f in features
              if min_group <= sum(1 for present, _ in samples if f in present) <= len(samples) - min_group]
    verdicts = []
    for index, feature in enumerate(sorted(tested)):
        with_values = [o for present, o in samples if feature in present]
        without_values = [o for present, o in samples if feature not in present]
        p = permutation_p(with_values, without_values, seed + index, rounds)
        adjusted = min(1.0, p * len(tested))
        passes = adjusted <= alpha
        verdicts.append(Verdict(
            feature=feature, with_feature=len(with_values), without_feature=len(without_values),
            rate_with=_rate(with_values), rate_without=_rate(without_values),
            difference=_rate(with_values) - _rate(without_values), p_value=p, p_adjusted=adjusted,
            passes=passes,
            reason=('beats chance after correction' if passes
                    else f'adjusted p {adjusted:.3f} above {alpha} over {len(tested)} tested')))
    return verdicts, len(tested)
