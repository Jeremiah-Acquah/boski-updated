import os
import re
from datetime import timedelta
from io import BytesIO
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageOps


def optimize_upload(field_file, max_side=1600, quality=85):
    """Shrink large phone photos before saving so pages load fast on mobile data."""
    if not field_file or getattr(field_file, "_committed", True):
        return
    try:
        field_file.file.seek(0)
        img = ImageOps.exif_transpose(Image.open(field_file.file))
        has_alpha = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )
        img.thumbnail((max_side, max_side))
        buf = BytesIO()
        if has_alpha:
            img.convert("RGBA").save(buf, "PNG", optimize=True)
            ext = ".png"
        else:
            img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
            ext = ".jpg"
        name = os.path.splitext(os.path.basename(field_file.name))[0] + ext
        field_file.save(name, ContentFile(buf.getvalue()), save=False)
    except Exception:
        # Not a readable image or an odd format: keep the original file untouched
        return


def normalize_phone(raw):
    """Digits only, and Ghana numbers like 024 123 4567 become 233241234567."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        digits = "233" + digits[1:]
    return digits


class StoreSettings(models.Model):
    """One row of store details that Boski can change from the admin."""

    store_name = models.CharField(max_length=100, default="Boski")
    tagline = models.CharField(
        max_length=200,
        blank=True,
        default="Quality goods imported from China to Ghana, on preorder.",
    )
    announcement = models.CharField(
        max_length=160,
        blank=True,
        default="Preorder from China on WhatsApp. Delivered to Ghana.",
        help_text="Short message in the thin bar at the very top of every page. Leave empty to hide it.",
    )
    whatsapp_number = models.CharField(
        max_length=20,
        help_text="International format, digits only. Example: 233241234567 "
        "(for 024 123 4567 in Ghana).",
    )
    whatsapp_display = models.CharField(
        max_length=30,
        blank=True,
        help_text="How the number looks on the site, e.g. +86 132 5057 6403. "
        "Leave empty to show it as +digits.",
    )
    email = models.EmailField(blank=True)
    location = models.CharField(max_length=150, blank=True, help_text="Example: Accra, Ghana")
    working_hours = models.CharField(
        max_length=150, blank=True, help_text="Example: Mon to Sat, 8am to 8pm"
    )
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Store settings"
        verbose_name_plural = "Store settings"

    def __str__(self):
        return "Store settings"

    def save(self, *args, **kwargs):
        # Keep digits only so the wa.me link always works
        self.whatsapp_number = "".join(c for c in self.whatsapp_number if c.isdigit())
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls(
                whatsapp_number=settings.WHATSAPP_NUMBER,
                whatsapp_display=getattr(settings, "WHATSAPP_DISPLAY", ""),
                store_name=settings.STORE_NAME,
            )
        return obj

    @property
    def phone_display(self):
        return self.whatsapp_display or f"+{self.whatsapp_number}"

    @property
    def whatsapp_link(self):
        return f"https://wa.me/{self.whatsapp_number}"


ICON_CHOICES = [
    ("", "Automatic (based on the category name)"),
    ("car", "Car"),
    ("tricycle", "Tricycle"),
    ("motorcycle", "Motorcycle"),
    ("electronics", "Electronics"),
    ("home", "Home and living"),
    ("fashion", "Fashion"),
    ("tools", "Tools and hardware"),
    ("beauty", "Beauty and care"),
    ("sports", "Sports and outdoors"),
    ("box", "Other"),
]

# Used when no icon is chosen: the first group with a whole word in the name wins
ICON_KEYWORDS = [
    ("tricycle", ("tricycle", "keke", "tuk")),
    ("motorcycle", ("motorcycle", "motorbike", "motor", "bike", "scooter")),
    ("car", ("car", "vehicle", "suv", "truck", "van", "bus", "auto")),
    ("electronics", ("electronic", "phone", "laptop", "computer", "gadget", "tv", "appliance")),
    ("home", ("home", "living", "furniture", "kitchen", "house")),
    ("fashion", ("fashion", "clothing", "clothes", "apparel", "shoe", "wear", "bag")),
    ("tools", ("tool", "hardware", "machine", "equipment", "spare")),
    ("beauty", ("beauty", "care", "cosmetic", "skin", "hair")),
    ("sports", ("sport", "outdoor", "fitness", "gym")),
]


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    image = models.ImageField(
        upload_to="categories/", blank=True, help_text="Optional picture for the category."
    )
    icon = models.CharField(
        max_length=20,
        blank=True,
        choices=ICON_CHOICES,
        help_text="Small icon shown next to the category name in the menu.",
    )
    order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers show first."
    )

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        optimize_upload(self.image, max_side=900)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shop:category", kwargs={"slug": self.slug})

    @property
    def icon_key(self):
        if self.icon:
            return self.icon
        tokens = re.findall(r"[a-z]+", self.name.lower())
        for key, words in ICON_KEYWORDS:
            for token in tokens:
                if any(token in (w, w + "s", w + "es") for w in words):
                    return key
        return "box"


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    short_description = models.CharField(
        max_length=200, blank=True, help_text="One line shown under the product name."
    )
    description = models.TextField(
        blank=True, help_text="Full details: specs, colours, sizes, etc."
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Required. The price tag customers will see, in the currency below.",
    )
    old_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Optional. The higher 'before' price. When filled in, the product shows "
        "as a deal with a percentage off.",
    )
    currency = models.CharField(
        max_length=5, default="GH₵", help_text="Shown before the price."
    )
    delivery_time = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: 4-6 weeks after payment.",
    )
    main_image = models.ImageField(upload_to="products/")
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide this product from the website."
    )
    is_featured = models.BooleanField(
        default=False, help_text="Show on the home page 'Featured' section."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def clean(self):
        if self.old_price is not None and self.price is not None and self.old_price <= self.price:
            raise ValidationError(
                {"old_price": "The old price must be higher than the current price."}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "product"
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        optimize_upload(self.main_image)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shop:product", kwargs={"slug": self.slug})

    def _money(self, value):
        return f"{self.currency} {value:,.2f}"

    @property
    def price_display(self):
        return self._money(self.price)

    @property
    def old_price_display(self):
        return self._money(self.old_price) if self.has_discount else ""

    @property
    def has_discount(self):
        return bool(self.old_price and self.old_price > self.price)

    @property
    def discount_percent(self):
        if not self.has_discount:
            return 0
        return int(round((1 - self.price / self.old_price) * 100))

    @property
    def is_new(self):
        return timezone.now() - self.created_at < timedelta(days=14)

    def whatsapp_url(self, request=None):
        """Link that opens WhatsApp chat with Boski and a prefilled preorder message."""
        number = StoreSettings.load().whatsapp_number
        link = self.get_absolute_url()
        if request is not None:
            link = request.build_absolute_uri(link)
        text = (
            f"Hello Boski, I would like to preorder:\n"
            f"*{self.name}*\n"
            f"Price: {self.price_display}\n"
            f"{link}"
        )
        return f"https://wa.me/{number}?text={quote(text)}"


class ProductImage(models.Model):
    """Extra gallery images for a product."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/gallery/")
    caption = models.CharField(max_length=150, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.product.name} image {self.pk}"

    def save(self, *args, **kwargs):
        optimize_upload(self.image)
        super().save(*args, **kwargs)


class Banner(models.Model):
    """Big slides at the top of the home page."""

    eyebrow = models.CharField(
        max_length=60, blank=True, default="BOSKI PRE-ORDER",
        help_text="Small line above the title.",
    )
    title = models.CharField(max_length=120, help_text="Example: Quality Vehicles from China")
    subtitle = models.CharField(
        max_length=200, blank=True, help_text="Example: Reliable. Affordable. Delivered to Ghana."
    )
    image = models.ImageField(
        upload_to="banners/",
        help_text="Wide photo, about 1600 x 600 pixels. Keep the left third plain so the text is readable.",
    )
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="The button opens this category. Leave empty to open all products.",
    )
    button_text = models.CharField(max_length=40, default="SHOP NOW")
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        optimize_upload(self.image, max_side=2000)
        super().save(*args, **kwargs)

    @property
    def url(self):
        return self.category.get_absolute_url() if self.category_id else reverse("shop:products")


class FAQ(models.Model):
    """Questions and answers shown on the Help page."""

    question = models.CharField(max_length=200)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class SourcingRequest(models.Model):
    """A customer asking Boski to find an item that is not listed."""

    name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, help_text="WhatsApp number of the customer.")
    item = models.TextField(verbose_name="What they want")
    budget = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False, help_text="Tick once you have replied.")

    class Meta:
        ordering = ["is_handled", "-created_at"]
        verbose_name = "item request"
        verbose_name_plural = "item requests"

    def __str__(self):
        return f"{self.name or self.phone}: {self.item[:40]}"

    @property
    def reply_url(self):
        number = normalize_phone(self.phone)
        text = quote(f"Hello {self.name or ''}, this is Boski. About your request: {self.item[:80]}".replace("  ", " "))
        return f"https://wa.me/{number}?text={text}"
