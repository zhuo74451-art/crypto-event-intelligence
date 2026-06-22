"""
Bootstrap confidence interval computation.
"""

from __future__ import annotations

import random
from typing import Callable, Optional

from ..contracts.evaluation import BootstrapResult, MetricValue
from ..contracts.common import BootstrapMethod


class IIDBootstrap:
    """IID bootstrap — resamples with replacement."""

    def __init__(self, n_iterations: int = 1000, seed: int = 42):
        self.n_iterations = n_iterations
        self.seed = seed
        self._rng = random.Random(seed)

    def compute_interval(
        self,
        values: list[float],
        metric_fn: Optional[Callable[[list[float]], float]] = None,
        alpha: float = 0.05,
    ) -> BootstrapResult:
        if metric_fn is None:
            metric_fn = lambda x: sum(x) / len(x) if x else 0.0

        if not values:
            return BootstrapResult(
                method=BootstrapMethod.IID,
                n_iterations=self.n_iterations,
                seed=self.seed,
            )

        n = len(values)
        bootstrap_stats = []
        for _ in range(self.n_iterations):
            sample = [self._rng.choice(values) for _ in range(n)]
            bootstrap_stats.append(metric_fn(sample))

        bootstrap_stats.sort()
        lower_idx = int(self.n_iterations * alpha / 2)
        upper_idx = int(self.n_iterations * (1 - alpha / 2))
        ci_lower = bootstrap_stats[lower_idx]
        ci_upper = bootstrap_stats[upper_idx]

        mean_val = sum(bootstrap_stats) / len(bootstrap_stats)
        std_err = (
            sum((x - mean_val) ** 2 for x in bootstrap_stats) / len(bootstrap_stats)
        ) ** 0.5

        return BootstrapResult(
            method=BootstrapMethod.IID,
            n_iterations=self.n_iterations,
            seed=self.seed,
            metric_values=bootstrap_stats,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            std_error=std_err,
        )


class BlockBootstrap:
    """Block bootstrap — resamples blocks for time series dependence."""

    def __init__(
        self,
        block_size: int = 5,
        n_iterations: int = 1000,
        seed: int = 42,
    ):
        self.block_size = block_size
        self.n_iterations = n_iterations
        self.seed = seed
        self._rng = random.Random(seed)

    def compute_interval(
        self,
        values: list[float],
        metric_fn: Optional[Callable[[list[float]], float]] = None,
        alpha: float = 0.05,
    ) -> BootstrapResult:
        if metric_fn is None:
            metric_fn = lambda x: sum(x) / len(x) if x else 0.0

        if not values:
            return BootstrapResult(
                method=BootstrapMethod.BLOCK,
                n_iterations=self.n_iterations,
                seed=self.seed,
            )

        n = len(values)
        n_blocks = (n + self.block_size - 1) // self.block_size
        bootstrap_stats = []

        for _ in range(self.n_iterations):
            sampled = []
            for _ in range(n_blocks):
                block_start = self._rng.randint(0, max(0, n - self.block_size))
                sampled.extend(values[block_start:block_start + self.block_size])
            sampled = sampled[:n]
            bootstrap_stats.append(metric_fn(sampled))

        bootstrap_stats.sort()
        lower_idx = int(self.n_iterations * alpha / 2)
        upper_idx = int(self.n_iterations * (1 - alpha / 2))
        ci_lower = bootstrap_stats[lower_idx]
        ci_upper = bootstrap_stats[upper_idx]

        mean_val = sum(bootstrap_stats) / len(bootstrap_stats)
        std_err = (
            sum((x - mean_val) ** 2 for x in bootstrap_stats) / len(bootstrap_stats)
        ) ** 0.5

        return BootstrapResult(
            method=BootstrapMethod.BLOCK,
            n_iterations=self.n_iterations,
            seed=self.seed,
            metric_values=bootstrap_stats,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            std_error=std_err,
        )


class EventClusterBootstrap:
    """Event cluster bootstrap — resamples event clusters for dependent events."""

    def __init__(
        self,
        n_iterations: int = 1000,
        seed: int = 42,
    ):
        self.n_iterations = n_iterations
        self.seed = seed
        self._rng = random.Random(seed)

    def compute_interval(
        self,
        cluster_values: dict[str, list[float]],
        metric_fn: Optional[Callable[[list[float]], float]] = None,
        alpha: float = 0.05,
    ) -> BootstrapResult:
        if metric_fn is None:
            metric_fn = lambda x: sum(x) / len(x) if x else 0.0

        if not cluster_values:
            return BootstrapResult(
                method=BootstrapMethod.EVENT_CLUSTER,
                n_iterations=self.n_iterations,
                seed=self.seed,
            )

        clusters = list(cluster_values.keys())
        bootstrap_stats = []

        for _ in range(self.n_iterations):
            sampled_clusters = [self._rng.choice(clusters) for _ in range(len(clusters))]
            sampled_values = []
            for c in sampled_clusters:
                sampled_values.extend(cluster_values[c])
            bootstrap_stats.append(metric_fn(sampled_values))

        bootstrap_stats.sort()
        lower_idx = int(self.n_iterations * alpha / 2)
        upper_idx = int(self.n_iterations * (1 - alpha / 2))
        ci_lower = bootstrap_stats[lower_idx]
        ci_upper = bootstrap_stats[upper_idx]

        mean_val = sum(bootstrap_stats) / len(bootstrap_stats)
        std_err = (
            sum((x - mean_val) ** 2 for x in bootstrap_stats) / len(bootstrap_stats)
        ) ** 0.5

        return BootstrapResult(
            method=BootstrapMethod.EVENT_CLUSTER,
            n_iterations=self.n_iterations,
            seed=self.seed,
            metric_values=bootstrap_stats,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            std_error=std_err,
        )
