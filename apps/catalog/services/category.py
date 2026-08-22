from django.db import transaction

from apps.catalog.models  import Category


class CategoryService:

    @staticmethod
    @transaction.atomic
    def create_category(
        *,
        name,
        slug,
        parent=None,
        description="",
    ):
        return Category.objects.create(
            name=name,
            slug=slug,
            parent=parent,
            description=description,
        )

    @staticmethod
    @transaction.atomic
    def move_category(
        *,
        category,
        parent,
    ):
        if parent == category:
            raise ValueError(
                "A category cannot be its own parent."
            )

        if parent and CategoryService._is_descendant(
            category=category,
            possible_parent=parent,
        ):
            raise ValueError(
                "A category cannot be moved under its descendant."
            )

        category.parent = parent
        category.save(
            update_fields=["parent", "updated_at"]
        )

        return category

    @staticmethod
    def _is_descendant(
        *,
        category,
        possible_parent,
    ):
        current = possible_parent

        while current is not None:
            if current.id == category.id:
                return True

            current = current.parent

        return False