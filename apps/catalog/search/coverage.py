from dataclasses import dataclass

from apps.catalog.search.factory import CatalogSearchFactory
from apps.catalog.search.evaluation_dataset import EVALUATION_DATASET


@dataclass(frozen=True)
class DatasetCoverage:
    total_expected: int
    found: int
    missing: tuple[str, ...]

    @property
    def coverage_rate(self) -> float:
        if self.total_expected == 0:
            return 1.0
        return self.found / self.total_expected


def validate_dataset_coverage(
    search_factory: CatalogSearchFactory,
) -> DatasetCoverage:
    expected_slugs = {
        slug
        for case in EVALUATION_DATASET
        for slug, relevance in case.relevance
        if relevance > 0
    }

    found_slugs = set(
        search_factory
        .queryset()
        .filter(slug__in=expected_slugs)
        .values_list("slug", flat=True)
    )

    missing = tuple(sorted(expected_slugs - found_slugs))

    return DatasetCoverage(
        total_expected=len(expected_slugs),
        found=len(found_slugs),
        missing=missing,
    )