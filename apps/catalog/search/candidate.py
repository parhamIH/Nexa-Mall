from dataclasses import dataclass
from typing import Callable, Iterable, Hashable, Tuple, Set, Dict

ProductId = Hashable
CandidateFetcher = Callable[[str, int], Iterable[ProductId]]

@dataclass(frozen=True)
class Candidate:
    product_id: ProductId
    channels: frozenset[str]

@dataclass(frozen=True)
class CandidateSet:
    candidates: tuple[Candidate, ...]

    @property
    def product_ids(self) -> tuple[ProductId, ...]:
        return tuple(
            candidate.product_id
            for candidate in self.candidates
        )

    def __len__(self) -> int:
        return len(self.candidates)

class CandidateGenerator:
    def __init__(
        self,
        fetchers: dict[str, CandidateFetcher],
        *,
        per_channel_limit: int = 50,
    ) -> None:
        if per_channel_limit <= 0:
            raise ValueError(
                "per_channel_limit must be greater than zero."
            )

        self.fetchers = fetchers
        self.per_channel_limit = per_channel_limit

    def generate(self, query: str) -> CandidateSet:
        query = query.strip()

        if not query:
            return CandidateSet(candidates=())

        channels_by_product: dict[
            ProductId,
            set[str],
        ] = {}

        for channel_name, fetcher in self.fetchers.items():
            product_ids = fetcher(
                query,
                self.per_channel_limit,
            )

            for product_id in product_ids:
                channels_by_product.setdefault(
                    product_id,
                    set(),
                ).add(channel_name)

        candidates = tuple(
            Candidate(
                product_id=product_id,
                channels=frozenset(channels),
            )
            for product_id, channels
            in channels_by_product.items()
        )

        return CandidateSet(
            candidates=candidates,
        )