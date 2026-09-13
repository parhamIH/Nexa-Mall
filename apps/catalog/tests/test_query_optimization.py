from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.catalog.api.serializers import ProductDetailSerializer
from apps.catalog.models import Product, ProductVariant
from apps.catalog.selectors.product import ProductSelector
from apps.tenants.models import Shop, Tenant


class ProductQueryOptimizationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Query Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Query Shop",
            slug="query-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Query Product",
            slug="query-product",
            status=Product.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.product,
            sku="QUERY-001",
            name="Black",
            price=Decimal("500000"),
            status=ProductVariant.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.product,
            sku="QUERY-002",
            name="White",
            price=Decimal("450000"),
            status=ProductVariant.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.product,
            sku="QUERY-003",
            name="Red",
            price=Decimal("700000"),
            status=ProductVariant.Status.ACTIVE,
        )

    def test_detail_read_has_fixed_query_budget(self):
        """
        Measure first, optimize second: the whole detail read
        (fetch + serialize) costs a FIXED query budget regardless
        of how many variants exist - no N+1, and the aggregate
        fields (count / min price) are computed by the database in
        the same query instead of Python loops.
        """

        with CaptureQueriesContext(
            connection,
        ) as queries:
            product = (
                ProductSelector.public_product_detail(
                    product_id=self.product.id,
                )
            )

            data = ProductDetailSerializer(
                product,
            ).data

        self.assertEqual(
            len(data["variants"]),
            3,
        )

        self.assertEqual(
            data["variant_count"],
            3,
        )

        self.assertEqual(
            Decimal(str(data["min_variant_price"])),
            Decimal("450000.00"),
        )

        # 1 main query (product + shop + brand + COUNT/MIN
        # annotations) + 3 prefetch queries (categories, images,
        # variants). Kept as an exact number on purpose: any new
        # relation added to the serializer must show up here and
        # be a conscious decision.
        self.assertEqual(
            len(queries),
            4,
        )

    def test_selector_computes_aggregates_in_the_database(self):
        product = (
            ProductSelector.public_product_detail(
                product_id=self.product.id,
            )
        )

        self.assertEqual(
            product.variant_count,
            3,
        )

        self.assertEqual(
            product.min_variant_price,
            Decimal("450000"),
        )

    def test_serialization_after_fetch_runs_no_queries(self):
        product = (
            ProductSelector.public_product_detail(
                product_id=self.product.id,
            )
        )

        with CaptureQueriesContext(
            connection,
        ) as queries:
            data = ProductDetailSerializer(
                product,
            ).data

        # Annotations + prefetches make the representation build
        # completely query-free: the method fields read attributes,
        # not relations.
        self.assertEqual(
            len(queries),
            0,
        )

        self.assertEqual(
            data["variant_count"],
            3,
        )

    def test_product_without_variants_annotates_zero_and_none(self):
        empty = Product.objects.create(
            shop=self.shop,
            name="Empty Product",
            slug="empty-product",
            status=Product.Status.ACTIVE,
        )

        detail = (
            ProductSelector.public_product_detail(
                product_id=empty.id,
            )
        )

        # SQL MIN over an empty join is NULL and COUNT is 0 - the
        # same semantics the old Python fallback produced.
        self.assertEqual(
            detail.variant_count,
            0,
        )

        self.assertIsNone(
            detail.min_variant_price,
        )

        data = ProductDetailSerializer(
            detail,
        ).data

        self.assertEqual(
            data["variant_count"],
            0,
        )

        self.assertIsNone(
            data["min_variant_price"],
        )
