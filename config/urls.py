from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from shop.sitemaps import CategorySitemap, ProductSitemap, StaticSitemap

admin.site.site_header = "Boski Admin"
admin.site.site_title = "Boski"
admin.site.index_title = "Manage your store"

sitemaps = {
    "pages": StaticSitemap,
    "categories": CategorySitemap,
    "products": ProductSitemap,
}

urlpatterns = [
    # Anyone who opens /admin/ (or anything under it) lands on the dashboard, which shows its own
    # login page first. The plain Django admin stays available at settings.ADMIN_URL as a backup.
    re_path(r"^admin(?:/.*)?$", RedirectView.as_view(pattern_name="dashboard:home", permanent=False), name="admin_redirect"),
    path(settings.ADMIN_URL, admin.site.urls),
    path(settings.DASHBOARD_URL, include("dashboard.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
    path("", include("shop.urls")),
]


# Serve uploaded product images from the configured media directory.

