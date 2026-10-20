# >>> The ONLY line you may need to change <<<
# Replace "store" with the name of the Django app that holds your models
# (the folder that contains models.py and the admin.py you shared).
from shop.models import (  # noqa: F401
    FAQ, Banner, Category, Product, ProductImage, SourcingRequest, StoreSettings,
)
