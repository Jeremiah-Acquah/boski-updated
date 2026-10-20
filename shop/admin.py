from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    FAQ,
    Banner,
    Category,
    Product,
    ProductImage,
    SourcingRequest,
    StoreSettings,
)


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ("store_name", "whatsapp_number", "whatsapp_display")
    fieldsets = (
        ("Store", {"fields": ("store_name", "tagline", "announcement")}),
        ("WhatsApp", {"fields": ("whatsapp_number", "whatsapp_display")}),
        ("Contact details", {"fields": ("email", "location", "working_hours")}),
        ("Social media", {"fields": ("facebook_url", "instagram_url", "tiktok_url")}),
    )

    def has_add_permission(self, request):
        # Only one settings row is needed
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "product_count", "order")
    list_editable = ("icon", "order")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ("image", "caption", "order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",
        "name",
        "category",
        "price_display",
        "old_price",
        "is_active",
        "is_featured",
        "created_at",
    )
    list_display_links = ("thumb", "name")
    list_filter = ("category", "is_active", "is_featured")
    list_editable = ("is_active", "is_featured")
    search_fields = ("name", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
    save_on_top = True
    actions = ["show_on_site", "hide_from_site", "mark_featured", "unmark_featured"]
    fieldsets = (
        (None, {"fields": ("category", "name", "slug", "main_image")}),
        ("Details", {"fields": ("short_description", "description", "delivery_time")}),
        ("Price", {"fields": ("price", "old_price", "currency")}),
        ("Visibility", {"fields": ("is_active", "is_featured")}),
    )

    @admin.display(description="Photo")
    def thumb(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" style="height:48px;width:48px;object-fit:cover;border-radius:6px">',
                obj.main_image.url,
            )
        return "-"

    @admin.action(description="Show selected products on the website")
    def show_on_site(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} product(s) are now visible.", messages.SUCCESS)

    @admin.action(description="Hide selected products from the website")
    def hide_from_site(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} product(s) are now hidden.", messages.SUCCESS)

    @admin.action(description="Feature selected products on the home page")
    def mark_featured(self, request, queryset):
        n = queryset.update(is_featured=True)
        self.message_user(request, f"{n} product(s) featured.", messages.SUCCESS)

    @admin.action(description="Remove selected products from Featured")
    def unmark_featured(self, request, queryset):
        n = queryset.update(is_featured=False)
        self.message_user(request, f"{n} product(s) un-featured.", messages.SUCCESS)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("thumb", "title", "category", "order", "is_active")
    list_display_links = ("thumb", "title")
    list_editable = ("order", "is_active")

    @admin.display(description="Banner")
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:44px;width:100px;object-fit:cover;border-radius:6px">',
                obj.image.url,
            )
        return "-"


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(SourcingRequest)
class SourcingRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "phone", "short_item", "budget", "is_handled", "reply")
    list_editable = ("is_handled",)
    list_filter = ("is_handled",)
    search_fields = ("name", "phone", "item")
    readonly_fields = ("created_at",)

    @admin.display(description="Request")
    def short_item(self, obj):
        return obj.item[:70] + ("..." if len(obj.item) > 70 else "")

    @admin.display(description="Reply")
    def reply(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Reply on WhatsApp</a>', obj.reply_url
        )
