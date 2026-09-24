from dataclasses import dataclass
from typing import Callable, Iterable, Tuple

from apps.catalog.search.benchmark import (
    SearchBenchmarkResult,
    run_search_benchmark,
)
from apps.catalog.search.ranking import (
    DEFAULT_RANKING_WEIGHTS,
    RankingWeights,
)


@dataclass(frozen=True)
class WeightSweepCandidate:
    name: str
    weights: RankingWeights


@dataclass(frozen=True)
class WeightSweepResult:
    name: str
    weights: RankingWeights
    benchmark: SearchBenchmarkResult

    @property
    def delta_precision_at_5(self) -> float:
        return 0.0

    @property
    def delta_recall_at_5(self) -> float:
        return 0.0

    @property
    def delta_mrr(self) -> float:
        return 0.0

    @property
    def delta_ndcg_at_5(self) -> float:
        return 0.0


def generate_single_variable_sweep(
    *,
    field_name: str,
    values: Iterable[float],
    baseline: RankingWeights = DEFAULT_RANKING_WEIGHTS,
) -> Tuple[WeightSweepCandidate, ...]:

    candidates = []

    for value in values:
        weights = RankingWeights(
            exact_name=(
                value
                if field_name == "exact_name"
                else baseline.exact_name
            ),
            sku=(
                value
                if field_name == "sku"
                else baseline.sku
            ),
            brand=(
                value
                if field_name == "brand"
                else baseline.brand
            ),
            name_trigram=(
                value
                if field_name == "name_trigram"
                else baseline.name_trigram
            ),
            full_text=(
                value
                if field_name == "full_text"
                else baseline.full_text
            ),
            description=(
                value
                if field_name == "description"
                else baseline.description
            ),
        )

        candidates.append(
            WeightSweepCandidate(
                name=f"{field_name}={value:g}",
                weights=weights,
            )
        )

    return tuple(candidates)


def run_weight_sweep(
    candidates: Iterable[WeightSweepCandidate],
    search_factory_builder: Callable[
        [RankingWeights],
        Callable[[str], list[str]],
    ],
) -> Tuple[WeightSweepResult, ...]:

    results = []

    for candidate in candidates:
        search = search_factory_builder(
            candidate.weights,
        )

        benchmark = run_search_benchmark(
            search,
        )

        results.append(
            WeightSweepResult(
                name=candidate.name,
                weights=candidate.weights,
                benchmark=benchmark,
            )
        )

    return tuple(results)