from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    # Hand-written on purpose: makemigrations cannot detect
    # extension requirements - the dependency must be the LATEST
    # catalog migration so pg_trgm exists before the trigram
    # indexes built by later migrations.
    dependencies = [
        (
            "catalog",
            "0002_productimage",
        ),
    ]

    operations = [
        TrigramExtension(),
    ]
