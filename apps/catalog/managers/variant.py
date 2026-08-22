from django.db import models


class ProductVariantQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            status=self.model.Status.ACTIVE
        )

    def inactive(self):
        return self.filter(
            status=self.model.Status.INACTIVE
        )

    def for_product(self, product):
        return self.filter(product=product)

    def with_relations(self):
        return (
            self
            .select_related(
                "product",
            )
            .prefetch_related(
                "option_values",
            )
        )


class ProductVariantManager(
    models.Manager.from_queryset(ProductVariantQuerySet)
):
    pass