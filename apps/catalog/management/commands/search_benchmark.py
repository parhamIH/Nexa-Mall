from django.core.management.base import BaseCommand

from apps.catalog.models import Shop, Product, Tenant
from apps.catalog.search.factory import CatalogSearchFactory
import time


class Command(BaseCommand):
    help = "Benchmark search performance (cache hot vs db path)."

    def add_arguments(self, parser):
        parser.add_argument('--tenant-id', type=int, required=True)
        parser.add_argument('--shop-id', type=int, required=True)
        parser.add_argument('--query', type=str, required=True)
        parser.add_argument('--mode', choices=['cache', 'db'], default='db',
                            help='Cache hot or DB path')
        parser.add_argument('--iterations', type=int, default=5,
                            help='Number of runs to measure')

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(pk=options['tenant_id'])
        shop = Shop.objects.get(pk=options['shop_id'])
        factory = CatalogSearchFactory.from_tenant_and_shop(
            tenant=tenant,
            shop=shop,
        )

        if options['mode'] == 'db':
            times = self.run_db_benchmark(factory, tenant, shop, options['query'], iterations=options['iterations'])
        else:
            times = self.run_cache_benchmark(factory, tenant, shop, options['query'], iterations=options['iterations'])

        p50, p95, p99 = self.compute_percentiles(times)
        self.stdout.write(self.style.SUCCESS(
            f"Mode: {options['mode']}\n"
            f"P50: {p50:.2f} ms\n"
            f"P95: {p95:.2f} ms\n"
            f"P99: {p99:.2f} ms\n"
        ))

    def run_db_benchmark(self, factory, tenant, shop, query, iterations):
        times = []
        for _ in range(iterations):
            queryset = factory.queryset().filter(
                shop_id=shop.id,
                shop__tenant_id=tenant.pk,
                name__icontains=query,
                status=Product.Status.ACTIVE,
            )
            start = time.perf_counter()
            _ = list(queryset)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # ms
        return times

    def run_cache_benchmark(self, factory, tenant, shop, query, iterations):
        cache = {}
        key = (tenant.pk, shop.id, query)
        queryset = factory.queryset().filter(
            shop_id=shop.id,
            shop__tenant_id=tenant.pk,
            name__icontains=query,
            status=Product.Status.ACTIVE,
        )
        start = time.perf_counter()
        _ = list(queryset)
        cache[key] = _  # store result
        end = time.perf_counter()
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            _ = cache[key]
            end = time.perf_counter()
            times.append((end - start) * 1000)  # ms
        return times

    @staticmethod
    def compute_percentiles(times):
        times_sorted = sorted(times)
        def percentile(p):
            k = (len(times_sorted) - 1) * (p / 100)
            f = int(k)
            c = min(f + 1, len(times_sorted) - 1)
            if f == c:
                return times_sorted[f]
            d0 = times_sorted[f] * (c - k)
            d1 = times_sorted[c] * (k - f)
            return d0 + d1
        p50 = percentile(50)
        p95 = percentile(95)
        p99 = percentile(99)
        return p50, p95, p99