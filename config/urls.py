
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.static import serve
from django.urls import re_path

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
    path(settings.ADMIN_URL, admin.site.urls),
    path(settings.DASHBOARD_URL, include("dashboard.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("", include("shop.urls")),
]

# Serve uploaded images from the persistent media directory.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
else:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
