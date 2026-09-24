from dataclasses import dataclass


@dataclass(frozen=True)
class RankingWeights:
    exact_name: float = 10.0
    sku: float = 8.0
    brand: float = 5.0
    name_trigram: float = 4.0
    full_text: float = 3.0
    description: float = 1.0


DEFAULT_RANKING_WEIGHTS = RankingWeights()