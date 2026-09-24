from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.catalog.search.coverage import validate_dataset_coverage
from apps.catalog.search.factory import (
    CatalogSearchFactory,
    InvalidSearchScope,
)
from apps.tenants.models import Tenant, Shop


class Command(BaseCommand):
    help = "Validate search evaluation dataset against a tenant/shop."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            required=True,
        )

        parser.add_argument(
            "--shop-id",
            required=True,
        )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError(
                "Search dataset validation requires PostgreSQL."
            )

        try:
            tenant = Tenant.objects.get(
                pk=options["tenant_id"],
            )
        except Tenant.DoesNotExist as exc:
            raise CommandError(
                "Tenant does not exist."
            ) from exc

        try:
            shop = Shop.objects.get(
                pk=options["shop_id"],
            )
        except Shop.DoesNotExist as exc:
            raise CommandError(
                "Shop does not exist."
            ) from exc

        try:
            factory = CatalogSearchFactory.from_tenant_and_shop(
                tenant=tenant,
                shop=shop,
            )
        except InvalidSearchScope as exc:
            raise CommandError(str(exc)) from exc

        coverage = validate_dataset_coverage(factory)

        self.stdout.write(
            f"Expected relevant products: {coverage.total_expected}"
        )

        self.stdout.write(
            f"Found: {coverage.found}"
        )

        self.stdout.write(
            f"Coverage: {coverage.coverage_rate:.2%}"
        )

        if coverage.missing:
            self.stdout.write(
                self.style.ERROR("Missing products:")
            )

            for slug in coverage.missing:
                self.stdout.write(f"  - {slug}")

            raise CommandError(
                "Evaluation dataset is incomplete."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Evaluation dataset coverage is complete."
            )
        )