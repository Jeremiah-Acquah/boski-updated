from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Category, Product


class StaticSitemap(Sitemap):
    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return ["shop:home", "shop:products", "shop:categories", "shop:faq", "shop:contact", "shop:about"]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return Category.objects.all()


class ProductSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at
