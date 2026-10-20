from .cart import Cart, wishlist_ids
from .models import Category, StoreSettings


def site_settings(request):
    """Store info, the category menu and cart/wishlist counters for every template."""
    saved = wishlist_ids(request)
    return {
        "store": StoreSettings.load(),
        "nav_categories": Category.objects.all(),
        "cart_count": Cart(request).count(),
        "wishlist_count": len(saved),
        "wishlist_set": set(saved),
    }
