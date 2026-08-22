from django.db import models


class ProductQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            status=self.model.Status.ACTIVE
        )

    def draft(self):
        return self.filter(
            status=self.model.Status.DRAFT
        )

    def archived(self):
        return self.filter(
            status=self.model.Status.ARCHIVED
        )

    def for_shop(self, shop):
        return self.filter(shop=shop)

    def with_relations(self):
        return (
            self
            .select_related(
                "shop",
                "brand",
            )
            .prefetch_related(
                "categories",
                "images",
                "options__values",
                "variants__option_values",
            )
        )


class ProductManager(
    models.Manager.from_queryset(ProductQuerySet)
):
    pass