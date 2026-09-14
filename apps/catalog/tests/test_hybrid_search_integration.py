from decimal import Decimal

from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.catalog.api.filters.hybrid_search import (
    HybridProductSearchFilter,
)
from apps.catalog.models import (
    Brand,
    Product,
    ProductVariant,
)
from apps.tenants.models import Shop, Tenant


class HybridSearchIntegrationTests(TestCase):
    """Level-2 search tests: the real database against the real
    HybridProductSearchFilter DIRECTLY - no endpoint, so
    authentication, permissions, pagination, serializers and the
    response contract stay out of the way; what remains under test
    is hybrid ranking alone.

    Ranking assertions follow two deliberately different strengths:
    - RANK assertions compare two products against each other
      (assertLess on indexes): a business INVARIANT such as
      "exact match > similar match" survives future ranking
      improvements, while assertEqual(result[0], ...) would break
      the moment a legitimately better result lands on top.
    - RECALL assertions (assertIn) only prove a product is FOUND:
      for typo queries the ranking position is not the contract
      yet - retrieval and ranking are different properties.
    """

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Integration Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Integration Shop",
            slug="integration-shop",
        )

        cls.brand = Brand.objects.create(
            name="Nike",
            slug="nike",
        )

        cls.exact_product = Product.objects.create(
            shop=cls.shop,
            name="Nike Air Max 270",
            slug="nike-air-max-270",
            description="Running shoes",
            brand=cls.brand,
            status=Product.Status.ACTIVE,
        )

        # Shares brand + partial name: a SIMILAR match that must
        # never outrank the exact one.
        cls.similar_product = Product.objects.create(
            shop=cls.shop,
            name="Nike Air Zoom",
            slug="nike-air-zoom",
            description="Running shoes",
            brand=cls.brand,
            status=Product.Status.ACTIVE,
        )

        cls.unrelated_product = Product.objects.create(
            shop=cls.shop,
            name="Wool Sweater",
            slug="wool-sweater",
            description="Winter clothing",
            status=Product.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.exact_product,
            sku="NK-AM-270",
            name="Black",
            price=Decimal("1000000"),
            status=ProductVariant.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.similar_product,
            sku="NK-AZ-90",
            name="White",
            price=Decimal("900000"),
            status=ProductVariant.Status.ACTIVE,
        )

        # Multi-tenant decoy: an IDENTICALLY named product in
        # another shop. Shop.tenant is OneToOne (each tenant has at
        # most one shop), so the second shop needs its own tenant.
        # A shop-scoped search must never return the decoy.
        cls.other_tenant = Tenant.objects.create(
            name="Other Tenant",
        )

        cls.other_shop = Shop.objects.create(
            tenant=cls.other_tenant,
            name="Other Shop",
            slug="other-shop",
        )

        cls.decoy_product = Product.objects.create(
            shop=cls.other_shop,
            name="Nike Air Max 270",
            slug="nike-air-max-270",
            description="Running shoes",
            status=Product.Status.ACTIVE,
        )

    def apply_search(self, query: str):
        factory = APIRequestFactory()

        # The filter reads request.query_params, which only exists
        # on a DRF Request - wrap the raw WSGIRequest exactly like
        # HybridSearchAdapter does.
        django_request = factory.get(
            "/api/v1/products/",
            {"search": query},
        )

        request = Request(django_request)

        # Shop scope BEFORE ranking (the multi-tenant contract):
        # isolation first, search second - never the reverse.
        queryset = Product.objects.filter(
            shop=self.shop,
        )

        return HybridProductSearchFilter().filter_queryset(
            request,
            queryset,
            view=None,
        )

    def result_slugs(self, query: str):
        return list(
            self.apply_search(query).values_list(
                "slug",
                flat=True,
            )
        )

    def test_exact_name_ranks_first(self):
        result = self.result_slugs("nike air max")

        self.assertTrue(result)

        self.assertEqual(
            result[0],
            self.exact_product.slug,
        )

    def test_exact_match_beats_similar_match(self):
        # Business invariant: exact > similar. Indexes, not absolute
        # positions - future ranking improvements may legitimately
        # reorder everything else around this pair.
        result = self.result_slugs("nike air max")

        self.assertIn(
            self.exact_product.slug,
            result,
        )

        self.assertIn(
            self.similar_product.slug,
            result,
        )

        self.assertLess(
            result.index(self.exact_product.slug),
            result.index(self.similar_product.slug),
        )

    def test_exact_sku_ranks_product_first(self):
        # SKU weight (8.0) is second only to exact name: a SKU match
        # must be worth far more than a weak description graze.
        result = self.result_slugs("NK-AM-270")

        self.assertTrue(result)

        self.assertEqual(
            result[0],
            self.exact_product.slug,
        )

    def test_typo_can_find_expected_product(self):
        # RECALL, not RANK: the typo'd query must still FIND the
        # product. websearch ANDs every token, so a typo in one
        # token kills the whole FTS path - only the trigram
        # candidate branch can rescue this (measured: similarity
        # 0.429 for the target vs 0.227 for the similar product,
        # threshold 0.3). Its position is not the contract yet.
        result = self.result_slugs("nkie air max")

        self.assertIn(
            self.exact_product.slug,
            result,
        )

    def result_ids(self, query: str):
        return list(
            self.apply_search(query).values_list(
                "id",
                flat=True,
            )
        )

    def test_shop_scope_is_respected(self):
        # The filter must never WIDEN the queryset it is given: the
        # identically-named decoy in another shop stays invisible to
        # a shop-scoped search. Compared by ID: slug (and name) are
        # only unique per shop, and the decoy deliberately reuses
        # both, so slug-based assertions could not tell the rows
        # apart.
        result = self.result_ids("nike air max")

        self.assertNotIn(
            self.decoy_product.id,
            result,
        )

        for product_id in result:
            self.assertNotEqual(
                product_id,
                self.decoy_product.id,
            )

    def test_unrelated_product_is_not_retrieved(self):
        result = self.result_slugs("nike air max")

        self.assertNotIn(
            self.unrelated_product.slug,
            result,
        )

