import django.core.validators
from django.db import migrations, models


def fill_missing_prices(apps, schema_editor):
    # Products saved before price became required get 0 so Boski can fix them in the admin.
    Product = apps.get_model("shop", "Product")
    Product.objects.filter(price__isnull=True).update(price=0)


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fill_missing_prices, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                help_text="Required. The price tag customers will see, in the currency below.",
            ),
        ),
    ]
