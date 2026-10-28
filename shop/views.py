import json
import time
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import cart as cart_tools
from .cart import Cart
from .forms import SourcingRequestForm
from .models import FAQ, Banner, Category, Product

PAGE_SIZE = 20

SORTS = {
    "newest": ("-created_at", "Newest first"),
    "price_asc": ("price", "Price: low to high"),
    "price_desc": ("-price", "Price: high to low"),
    "name": ("name", "Name: A to Z"),
}


def _active_products():
    return Product.objects.filter(is_active=True).select_related("category")


def _deals(products):
    return products.filter(old_price__isnull=False, old_price__gt=F("price"))


def _decimal(value):
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number >= 0 else None


def _safe_next(request, fallback):
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return fallback


# ---------------------------------------------------------------- home


def _hero_slides(featured, latest):
    """Banners Boski added in the admin; otherwise slides built from products."""
    slides = [
        {
            "eyebrow": b.eyebrow,
            "title": b.title,
            "subtitle": b.subtitle,
            "image": b.image.url,
            "url": b.url,
            "button": b.button_text,
        }
        for b in Banner.objects.filter(is_active=True).select_related("category")
    ]
    if slides:
        return slides
    source = featured or latest
    slides = [
        {
            "eyebrow": "BOSKI PRE-ORDER",
            "title": p.name,
            "subtitle": p.short_description or "Preorder now. Delivered to Ghana.",
            "image": p.main_image.url,
            "url": p.get_absolute_url(),
            "button": "VIEW PRODUCT",
        }
        for p in source[:4]
    ]
    if slides:
        return slides
    return [
        {
            "eyebrow": "BOSKI PRE-ORDER",
            "title": "Quality goods from China",
            "subtitle": "Reliable. Affordable. Delivered to Ghana.",
            "image": "",
            "url": reverse("shop:products"),
            "button": "SHOP NOW",
        }
    ]


def _promo_tiles(products):
    """Three tiles under the banner, one per category that has products."""
    tiles = []
    styles = ["one", "two", "three"]
    leads = ["Explore", "Available", "Latest"]
    for category in Category.objects.all():
        newest = products.filter(category=category).first()
        if newest is None:
            continue
        image = category.image.url if category.image else newest.main_image.url
        tiles.append(
            {
                "category": category,
                "image": image,
                "style": styles[len(tiles)],
                "lead": leads[len(tiles)],
            }
        )
        if len(tiles) == 3:
            break
    return tiles


def home(request):
    products = _active_products()
    featured = list(products.filter(is_featured=True)[:10])
    latest = list(products[:10])
    featured_ids = [p.pk for p in featured]
    rows = []
    for category in Category.objects.all():
        items = list(products.filter(category=category)[:5])
        if items:
            rows.append({"category": category, "products": items})
        if len(rows) == 3:
            break
    context = {
        "slides": _hero_slides(featured, latest),
        "tiles": _promo_tiles(products),
        "featured": featured,
        "deals": list(_deals(products)[:5]),
        "new_arrivals": list(products.exclude(pk__in=featured_ids)[:5]),
        "category_rows": rows,
        "recent": cart_tools.recently_viewed(request),
        "categories": Category.objects.all(),
        "has_products": bool(latest),
    }
    return render(request, "shop/home.html", context)


# ------------------------------------------------------------- listings


def _listing(request, products, *, title, subtitle="", current_category=None, q=""):
    """Shared product listing: price filter, deals only, sorting and pagination."""
    min_price = _decimal(request.GET.get("min", ""))
    max_price = _decimal(request.GET.get("max", ""))
    deals_only = request.GET.get("deals") == "1"
    sort = request.GET.get("sort", "newest")
    if sort not in SORTS:
        sort = "newest"

    if min_price is not None:
        products = products.filter(price__gte=min_price)
    if max_price is not None:
        products = products.filter(price__lte=max_price)
    if deals_only:
        products = _deals(products)
    products = products.order_by(SORTS[sort][0], "-id")

    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    categories = Category.objects.annotate(
        n=Count("products", filter=Q(products__is_active=True))
    )
    context = {
        "page": page,
        "title": title,
        "subtitle": subtitle,
        "current_category": current_category,
        "q": q,
        "sort": sort,
        "sorts": [(key, label) for key, (_, label) in SORTS.items()],
        "min_price": request.GET.get("min", "") if min_price is not None else "",
        "max_price": request.GET.get("max", "") if max_price is not None else "",
        "deals_only": deals_only,
        "querystring": params.urlencode(),
        "filter_categories": categories,
        "filters_active": bool(min_price is not None or max_price is not None or deals_only),
    }
    return render(request, "shop/listing.html", context)


def product_list(request):
    products = _active_products()
    current = None
    slug = request.GET.get("category", "")
    if slug:
        current = Category.objects.filter(slug=slug).first()
        if current:
            products = products.filter(category=current)
    title = current.name if current else "All Products"
    if request.GET.get("deals") == "1" and not current:
        title = "Deals"
    return _listing(request, products, title=title, current_category=current)


def category_list(request):
    categories = Category.objects.annotate(
        n=Count("products", filter=Q(products__is_active=True))
    )
    return render(request, "shop/category_list.html", {"categories": categories})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = _active_products().filter(category=category)
    return _listing(request, products, title=category.name, current_category=category)


def search(request):
    q = request.GET.get("q", "").strip()
    slug = request.GET.get("category", "")
    products = _active_products()
    current = None
    if slug:
        current = Category.objects.filter(slug=slug).first()
        if current:
            products = products.filter(category=current)
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(short_description__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )
        title = f'Results for "{q}"'
    elif current:
        title = current.name
    else:
        products = products.none()
        title = "Search"
    return _listing(request, products, title=title, current_category=current, q=q)


# ------------------------------------------------------------- product


def product_detail(request, slug):
    product = get_object_or_404(_active_products(), slug=slug)
    gallery = [{"url": product.main_image.url, "caption": product.name}]
    gallery += [
        {"url": img.image.url, "caption": img.caption or product.name}
        for img in product.images.all()
    ]
    related = (
        _active_products()
        .filter(category=product.category)
        .exclude(pk=product.pk)[:5]
    )
    recent = cart_tools.recently_viewed(request, exclude_id=product.pk)
    cart_tools.remember_viewed(request, product.pk)
    absolute = request.build_absolute_uri(product.get_absolute_url())
    currency = product.currency.strip()
    currency_code = "GHS" if currency in ("GH₵", "GHS", "GHC", "GH¢") else (
        currency if len(currency) == 3 and currency.isalpha() else ""
    )
    offer = {
        "@type": "Offer",
        "price": str(product.price),
        "availability": "https://schema.org/PreOrder",
        "url": absolute,
    }
    if currency_code:
        offer["priceCurrency"] = currency_code
    jsonld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.name,
            "image": [request.build_absolute_uri(product.main_image.url)],
            "description": product.short_description or product.name,
            "category": product.category.name,
            "offers": offer,
        }
    ).replace("<", "\\u003c")
    return render(
        request,
        "shop/product.html",
        {
            "jsonld": jsonld,
            "product": product,
            "gallery": gallery,
            "related": related,
            "recent": recent,
            "whatsapp_url": product.whatsapp_url(request),
            "absolute_url": absolute,
            "og_image": request.build_absolute_uri(product.main_image.url),
            "currency_code": currency_code,
            "in_cart": Cart(request).data.get(str(product.pk), 0),
        },
    )


# ---------------------------------------------------- preorder list (cart)


def cart_view(request):
    cart = Cart(request)
    rows = cart.items()
    total, currency = Cart.total(rows)
    return render(
        request,
        "shop/cart.html",
        {
            "rows": rows,
            "total": total,
            "currency": currency,
            "whatsapp_url": cart.whatsapp_url(rows, total, currency) if rows else "",
        },
    )


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    try:
        qty = int(request.POST.get("qty", 1))
    except ValueError:
        qty = 1
    Cart(request).add(product, qty)
    messages.success(request, f"{product.name} was added to your preorder list.")
    return redirect(_safe_next(request, reverse("shop:cart")))


@require_POST
def cart_update(request, pk):
    try:
        qty = int(request.POST.get("qty", 1))
    except ValueError:
        qty = 1
    Cart(request).set_qty(pk, qty)
    return redirect("shop:cart")


@require_POST
def cart_remove(request, pk):
    Cart(request).remove(pk)
    return redirect("shop:cart")


@require_POST
def cart_clear(request):
    Cart(request).clear()
    return redirect("shop:cart")


# ------------------------------------------------------------ wishlist


def wishlist_view(request):
    ids = cart_tools.wishlist_ids(request)
    products = {p.pk: p for p in _active_products().filter(pk__in=ids)}
    items = [products[i] for i in ids if i in products]
    return render(request, "shop/wishlist.html", {"items": items})


@require_POST
def wishlist_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    saved = cart_tools.toggle_wishlist(request, product.pk)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {"saved": saved, "count": len(cart_tools.wishlist_ids(request))}
        )
    return redirect(_safe_next(request, product.get_absolute_url()))


# -------------------------------------------------------- info pages


def about(request):
    return render(request, "shop/about.html")

def privacy_policy(request):
    return render(request, "shop/privacy_policy.html")


def terms(request):
    return render(request, "shop/terms.html")


def faq(request):
    return render(request, "shop/faq.html", {"faqs": FAQ.objects.filter(is_active=True)})


def contact(request):
    form = SourcingRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if time.time() - request.session.get("last_request_at", 0) < 20:
            form.add_error(None, "Please wait a few seconds before sending another request.")
        else:
            item = form.save()
            request.session["last_request_at"] = time.time()
            messages.success(
                request,
                "Thank you. Your request was sent and Boski will reply on WhatsApp.",
            )
            return redirect(f"{reverse('shop:contact')}#request")
    return render(request, "shop/contact.html", {"form": form})


def robots_txt(request):
    from django.conf import settings

    lines = ["User-agent: *"]
    # Only the default admin address is listed. A custom (private) address must stay out of this
    # public file, otherwise robots.txt would tell everyone where it is.
    lines.append("Disallow: /admin/")
    if settings.DASHBOARD_URL == "manage/":
        lines.append("Disallow: /manage/")
    lines += [
        "Disallow: /cart/",
        "Disallow: /wishlist/",
        "",
        f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
