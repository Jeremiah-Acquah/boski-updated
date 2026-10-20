"""Session based 'preorder list' (cart), wishlist and recently viewed.

Nothing here needs a customer account: everything is kept in the visitor's session.
The preorder list is sent to Boski as one WhatsApp message.
"""
from decimal import Decimal
from urllib.parse import quote

from .models import Product, StoreSettings

CART_KEY = "cart"
WISHLIST_KEY = "wishlist"
RECENT_KEY = "recent"
MAX_QTY = 99
MAX_RECENT = 10


class Cart:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        self.data = dict(self.session.get(CART_KEY, {}))

    def _save(self):
        self.session[CART_KEY] = self.data
        self.session.modified = True

    def add(self, product, qty=1):
        key = str(product.pk)
        self.data[key] = min(MAX_QTY, self.data.get(key, 0) + max(1, qty))
        self._save()

    def set_qty(self, product_id, qty):
        key = str(product_id)
        if key not in self.data:
            return
        if qty <= 0:
            del self.data[key]
        else:
            self.data[key] = min(MAX_QTY, qty)
        self._save()

    def remove(self, product_id):
        if self.data.pop(str(product_id), None) is not None:
            self._save()

    def clear(self):
        self.data = {}
        self._save()

    def items(self):
        products = Product.objects.filter(
            pk__in=[int(k) for k in self.data], is_active=True
        ).select_related("category")
        by_id = {p.pk: p for p in products}
        rows = []
        for key, qty in self.data.items():
            product = by_id.get(int(key))
            if product is None:
                continue
            rows.append(
                {"product": product, "qty": qty, "line_total": product.price * qty}
            )
        return rows

    def count(self):
        return sum(self.data.values())

    @staticmethod
    def total(rows):
        """Total and currency, or (None, '') when currencies are mixed or the list is empty."""
        currencies = {r["product"].currency for r in rows}
        if len(currencies) != 1:
            return None, ""
        return sum((r["line_total"] for r in rows), Decimal("0")), currencies.pop()

    def whatsapp_url(self, rows, total, currency):
        number = StoreSettings.load().whatsapp_number
        lines = ["Hello Boski, I would like to preorder these items:", ""]
        for i, r in enumerate(rows, 1):
            p = r["product"]
            link = self.request.build_absolute_uri(p.get_absolute_url())
            lines.append(f"{i}. {p.name} x{r['qty']} ({p.price_display} each)")
            lines.append(f"   {link}")
        if total is not None:
            lines += ["", f"Estimated total: {currency} {total:,.2f}"]
        lines += ["", "Please confirm availability, payment and delivery time."]
        return f"https://wa.me/{number}?text={quote(chr(10).join(lines))}"


def wishlist_ids(request):
    return [int(i) for i in request.session.get(WISHLIST_KEY, []) if str(i).isdigit()]


def toggle_wishlist(request, product_id):
    """Add or remove a product. Returns True when it is now saved."""
    ids = wishlist_ids(request)
    if product_id in ids:
        ids.remove(product_id)
        saved = False
    else:
        ids.insert(0, product_id)
        saved = True
    request.session[WISHLIST_KEY] = ids[:200]
    request.session.modified = True
    return saved


def remember_viewed(request, product_id):
    ids = [i for i in request.session.get(RECENT_KEY, []) if i != product_id]
    ids.insert(0, product_id)
    request.session[RECENT_KEY] = ids[:MAX_RECENT]
    request.session.modified = True


def recently_viewed(request, exclude_id=None, limit=5):
    ids = [i for i in request.session.get(RECENT_KEY, []) if i != exclude_id][:limit]
    if not ids:
        return []
    products = {
        p.pk: p
        for p in Product.objects.filter(pk__in=ids, is_active=True).select_related("category")
    }
    return [products[i] for i in ids if i in products]
