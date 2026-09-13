from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Audit the REAL indexes/constraints the database has for "
        "every model and compare them with what the models declare "
        "(drift check). Run this BEFORE any index migration: index "
        "decisions follow the measured database state, not guesses."
    )

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for model in apps.get_models():
                table = model._meta.db_table

                constraints = (
                    connection.introspection.get_constraints(
                        cursor,
                        table,
                    )
                )

                indexes = []

                for name, info in constraints.items():
                    if info.get("index") or info.get("unique"):
                        indexes.append(
                            {
                                "name": name,
                                "columns": info.get(
                                    "columns"
                                ),
                                "unique": info.get(
                                    "unique"
                                ),
                                "primary_key": info.get(
                                    "primary_key"
                                ),
                            }
                        )

                declared = getattr(
                    model._meta,
                    "indexes",
                    [],
                )

                declared_names = {
                    index.name
                    for index in declared
                }

                self.stdout.write(
                    "=" * 70
                )

                self.stdout.write(
                    model._meta.label
                )

                self.stdout.write(
                    table
                )

                self.stdout.write(
                    "=" * 70
                )

                for index in sorted(
                    indexes,
                    key=lambda item: item["name"],
                ):
                    self.stdout.write(
                        f"  {index}"
                    )

                if not indexes:
                    self.stdout.write(
                        "  (no indexes)"
                    )

                self.stdout.write(
                    f"  declared in Meta.indexes: "
                    f"{sorted(declared_names) or 'none'}"
                )

                self.stdout.write("")
