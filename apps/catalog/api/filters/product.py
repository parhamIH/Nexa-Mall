import django_filters

from apps.catalog.models import Product


class ProductFilter(django_filters.FilterSet):

    status = django_filters.MultipleChoiceFilter(
        field_name="status",
        choices=Product.Status.choices,
    )

    brand = django_filters.UUIDFilter(
        field_name="brand_id",
    )

    category = django_filters.UUIDFilter(
        field_name="categories__id",
    )

    shop = django_filters.UUIDFilter(
        field_name="shop_id",
    )

    class Meta:
        model = Product
        fields = [
            "status",
            "brand",
            "category",
            "shop",
        ]