import shutil
import tempfile
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import (
    FAQ,
    Banner,
    Category,
    Product,
    ProductImage,
    SourcingRequest,
    StoreSettings,
    normalize_phone,
)

TEMP_MEDIA = tempfile.mkdtemp()


def fake_image(name="x.jpg", color=(30, 90, 120)):
    buf = BytesIO()
    Image.new("RGB", (80, 60), color).save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ShopTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        StoreSettings.objects.create(whatsapp_number="+233 24 123 4567")
        self.cars = Category.objects.create(name="Cars")
        self.trikes = Category.objects.create(name="Tricycles & Motorcycles")
        self.car = Product.objects.create(
            category=self.cars,
            name="Toyota Corolla 2020",
            short_description="Clean and fuel efficient",
            description="Full details here",
            price=85000,
            main_image=fake_image("car.jpg"),
        )
        ProductImage.objects.create(product=self.car, image=fake_image("car2.jpg"))
        ProductImage.objects.create(product=self.car, image=fake_image("car3.jpg"))
        self.hidden = Product.objects.create(
            category=self.cars, name="Hidden car", price=1000,
            main_image=fake_image("h.jpg"), is_active=False,
        )

    def test_whatsapp_number_is_cleaned_to_digits(self):
        self.assertEqual(StoreSettings.load().whatsapp_number, "233241234567")

    def test_slugs_are_generated_and_unique(self):
        dup = Product.objects.create(
            category=self.cars, name="Toyota Corolla 2020", price=1, main_image=fake_image()
        )
        self.assertEqual(self.car.slug, "toyota-corolla-2020")
        self.assertEqual(dup.slug, "toyota-corolla-2020-2")
        self.assertEqual(self.trikes.slug, "tricycles-motorcycles")

    def test_home_page(self):
        r = self.client.get(reverse("shop:home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Toyota Corolla 2020")
        self.assertContains(r, "Tricycles &amp; Motorcycles")
        self.assertNotContains(r, "Hidden car")

    def test_category_page(self):
        r = self.client.get(self.cars.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Toyota Corolla 2020")
        empty = self.client.get(self.trikes.get_absolute_url())
        self.assertContains(empty, "Nothing here yet")

    def test_product_detail_has_gallery_and_whatsapp_link(self):
        r = self.client.get(self.car.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["gallery"]), 3)
        self.assertContains(r, "Full details here")
        url = r.context["whatsapp_url"]
        parsed = urlparse(url)
        self.assertEqual(parsed.netloc, "wa.me")
        self.assertEqual(parsed.path, "/233241234567")
        text = parse_qs(parsed.query)["text"][0]
        self.assertIn("Toyota Corolla 2020", text)
        self.assertIn(self.car.get_absolute_url(), text)

    def test_inactive_product_is_404(self):
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)

    def test_search(self):
        r = self.client.get(reverse("shop:search"), {"q": "corolla"})
        self.assertContains(r, "Toyota Corolla 2020")
        r = self.client.get(reverse("shop:search"), {"q": "zzzz"})
        self.assertContains(r, "No match")
        self.assertEqual(self.client.get(reverse("shop:search")).status_code, 200)

    def test_admin_pages_work_for_superuser(self):
        User = get_user_model()
        User.objects.create_superuser("boski", "b@example.com", "pass12345!")
        self.client.login(username="boski", password="pass12345!")
        for name in (
            "admin:shop_category_changelist",
            "admin:shop_product_changelist",
            "admin:shop_product_add",
            "admin:shop_storesettings_changelist",
            "admin:shop_banner_changelist",
            "admin:shop_banner_add",
        ):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        r = self.client.get(reverse("admin:shop_product_change", args=[self.car.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "car2")  # inline extra images are editable

    def test_price_is_required_in_admin(self):
        User = get_user_model()
        User.objects.create_superuser("boski", "b@example.com", "pass12345!")
        self.client.login(username="boski", password="pass12345!")
        r = self.client.post(
            reverse("admin:shop_product_add"),
            {
                "category": self.cars.pk, "name": "No price car", "slug": "no-price-car",
                "main_image": fake_image("n.jpg"), "currency": "GH₵",
                "images-TOTAL_FORMS": 0, "images-INITIAL_FORMS": 0,
                "images-MIN_NUM_FORMS": 0, "images-MAX_NUM_FORMS": 1000,
            },
        )
        self.assertEqual(r.status_code, 200)  # form redisplayed with an error
        self.assertFalse(Product.objects.filter(name="No price car").exists())
        self.assertFormError(r.context["adminform"].form, "price", "This field is required.")

    def test_home_uses_banners_when_added_and_falls_back_to_products(self):
        r = self.client.get(reverse("shop:home"))
        self.assertEqual(r.context["slides"][0]["title"], "Toyota Corolla 2020")
        Banner.objects.create(
            title="Quality Vehicles from China", image=fake_image("b.jpg"),
            category=self.cars, button_text="SHOP CARS", order=0,
        )
        Banner.objects.create(
            title="Hidden banner", image=fake_image("b2.jpg"), is_active=False,
        )
        r = self.client.get(reverse("shop:home"))
        titles = [s["title"] for s in r.context["slides"]]
        self.assertEqual(titles, ["Quality Vehicles from China"])
        self.assertContains(r, "SHOP CARS")
        self.assertEqual(r.context["slides"][0]["url"], self.cars.get_absolute_url())

    def test_home_without_any_products_still_renders(self):
        Product.objects.all().delete()
        r = self.client.get(reverse("shop:home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No products yet")

    def test_new_pages(self):
        r = self.client.get(reverse("shop:products"))
        self.assertContains(r, "Toyota Corolla 2020")
        self.assertNotContains(r, "Hidden car")
        r = self.client.get(reverse("shop:products"), {"category": self.trikes.slug})
        self.assertContains(r, "Nothing here yet")
        self.assertEqual(self.client.get(reverse("shop:categories")).status_code, 200)
        self.assertEqual(self.client.get(reverse("shop:about")).status_code, 200)

    def test_search_can_filter_by_category(self):
        r = self.client.get(reverse("shop:search"), {"category": self.cars.slug})
        self.assertContains(r, "Toyota Corolla 2020")
        r = self.client.get(reverse("shop:search"), {"q": "corolla", "category": self.trikes.slug})
        self.assertContains(r, "No match")

    def test_category_icons_are_guessed_from_whole_words(self):
        guesses = {
            "Cars": "car",
            "Tricycles": "tricycle",
            "Motorcycles": "motorcycle",
            "Electronics": "electronics",
            "Beauty & Personal Care": "beauty",
            "Tools & Hardware": "tools",
            "Other Products": "box",
        }
        for name, icon in guesses.items():
            self.assertEqual(Category(name=name).icon_key, icon, name)
        self.assertEqual(Category(name="Cars", icon="home").icon_key, "home")

    def test_phone_display(self):
        s = StoreSettings.load()
        self.assertEqual(s.phone_display, "+233241234567")
        s.whatsapp_display = "+233 24 123 4567"
        self.assertEqual(s.phone_display, "+233 24 123 4567")

    def test_category_with_products_cannot_be_deleted(self):
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.cars.delete()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class MarketplaceFeatureTests(TestCase):
    """Preorder list, wishlist, deals, filters, contact form and SEO files."""

    def setUp(self):
        StoreSettings.objects.create(whatsapp_number="233241234567")
        self.cat = Category.objects.create(name="Electronics")
        self.tv = Product.objects.create(
            category=self.cat, name="Smart TV", price=3000, old_price=4000,
            main_image=fake_image("tv.jpg"),
        )
        self.buds = Product.objects.create(
            category=self.cat, name="Earbuds", price=250, main_image=fake_image("e.jpg"),
        )
        self.off = Product.objects.create(
            category=self.cat, name="Hidden item", price=10, main_image=fake_image("o.jpg"),
            is_active=False,
        )

    # --- prices and deals
    def test_discount_maths(self):
        self.assertTrue(self.tv.has_discount)
        self.assertEqual(self.tv.discount_percent, 25)
        self.assertEqual(self.tv.old_price_display, "GH₵ 4,000.00")
        self.assertFalse(self.buds.has_discount)
        self.assertEqual(self.buds.old_price_display, "")

    def test_old_price_must_be_higher_than_price(self):
        from django.core.exceptions import ValidationError

        bad = Product(category=self.cat, name="Bad", price=100, old_price=90)
        with self.assertRaises(ValidationError):
            bad.full_clean(exclude=["main_image", "slug"])

    def test_deals_filter_price_range_and_sort(self):
        url = reverse("shop:products")
        r = self.client.get(url, {"deals": "1"})
        names = [p.name for p in r.context["page"].object_list]
        self.assertEqual(names, ["Smart TV"])
        r = self.client.get(url, {"min": "100", "max": "500"})
        self.assertEqual([p.name for p in r.context["page"].object_list], ["Earbuds"])
        r = self.client.get(url, {"sort": "price_asc"})
        self.assertEqual([p.name for p in r.context["page"].object_list], ["Earbuds", "Smart TV"])
        # nonsense input never crashes the page
        r = self.client.get(url, {"min": "abc", "max": "-5", "sort": "drop table", "page": "999"})
        self.assertEqual(r.status_code, 200)

    # --- preorder list (cart)
    def test_cart_add_update_remove_and_whatsapp_message(self):
        add = reverse("shop:cart_add", args=[self.tv.pk])
        self.client.post(add, {"qty": "2"})
        self.client.post(reverse("shop:cart_add", args=[self.buds.pk]), {"qty": "1"})
        r = self.client.get(reverse("shop:cart"))
        self.assertEqual(len(r.context["rows"]), 2)
        self.assertEqual(str(r.context["total"]), "6250.00")
        self.assertContains(r, "GH₵ 6,250.00")  # thousands separators on the page too
        self.assertContains(r, "GH₵ 6,000.00")
        parsed = urlparse(r.context["whatsapp_url"])
        self.assertEqual(parsed.path, "/233241234567")
        text = parse_qs(parsed.query)["text"][0]
        self.assertIn("Smart TV x2", text)
        self.assertIn("Estimated total: GH₵ 6,250.00", text)

        self.client.post(reverse("shop:cart_update", args=[self.tv.pk]), {"qty": "5"})
        rows = self.client.get(reverse("shop:cart")).context["rows"]
        self.assertEqual([r["qty"] for r in rows if r["product"] == self.tv], [5])
        self.client.post(reverse("shop:cart_remove", args=[self.tv.pk]))
        self.assertEqual(len(self.client.get(reverse("shop:cart")).context["rows"]), 1)
        self.client.post(reverse("shop:cart_clear"))
        self.assertEqual(self.client.get(reverse("shop:cart")).context["rows"], [])

    def test_cart_rules(self):
        # a hidden product cannot be added; quantity is capped; GET is not allowed
        self.assertEqual(
            self.client.post(reverse("shop:cart_add", args=[self.off.pk])).status_code, 404
        )
        self.client.post(reverse("shop:cart_add", args=[self.buds.pk]), {"qty": "5000"})
        self.assertEqual(self.client.get(reverse("shop:cart")).context["rows"][0]["qty"], 99)
        self.assertEqual(
            self.client.get(reverse("shop:cart_add", args=[self.buds.pk])).status_code, 405
        )
        self.client.post(reverse("shop:cart_add", args=[self.buds.pk]), {"qty": "abc"})  # no crash

    def test_cart_ignores_redirect_to_other_sites(self):
        r = self.client.post(
            reverse("shop:cart_add", args=[self.buds.pk]), {"next": "https://evil.example/x"}
        )
        self.assertEqual(r["Location"], reverse("shop:cart"))

    def test_mixed_currencies_show_no_total(self):
        usd = Product.objects.create(
            category=self.cat, name="Imported gadget", price=50, currency="USD",
            main_image=fake_image("u.jpg"),
        )
        self.client.post(reverse("shop:cart_add", args=[usd.pk]))
        self.client.post(reverse("shop:cart_add", args=[self.buds.pk]))
        r = self.client.get(reverse("shop:cart"))
        self.assertIsNone(r.context["total"])
        text = parse_qs(urlparse(r.context["whatsapp_url"]).query)["text"][0]
        self.assertNotIn("Estimated total", text)

    # --- wishlist and recently viewed
    def test_wishlist_toggle(self):
        url = reverse("shop:wishlist_toggle", args=[self.tv.pk])
        r = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.json(), {"saved": True, "count": 1})
        self.assertContains(self.client.get(reverse("shop:wishlist")), "Smart TV")
        r = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.json(), {"saved": False, "count": 0})

    def test_recently_viewed_shows_other_products(self):
        self.client.get(self.tv.get_absolute_url())
        r = self.client.get(self.buds.get_absolute_url())
        self.assertEqual([p.name for p in r.context["recent"]], ["Smart TV"])

    # --- contact / item requests
    def test_contact_form_saves_request(self):
        data = {"name": "Ama", "phone": "024 555 1234", "item": "A cargo tricycle", "budget": "GH₵ 20,000"}
        r = self.client.post(reverse("shop:contact"), data)
        self.assertEqual(r.status_code, 302)
        req = SourcingRequest.objects.get()
        self.assertEqual(req.name, "Ama")
        self.assertFalse(req.is_handled)
        self.assertTrue(req.reply_url.startswith("https://wa.me/233245551234"))

    def test_contact_form_rejects_bad_phone_and_spam(self):
        bad_phone = {"name": "A", "phone": "123", "item": "x"}
        self.assertEqual(self.client.post(reverse("shop:contact"), bad_phone).status_code, 200)
        spam = {"name": "Bot", "phone": "0245551234", "item": "buy now", "website": "http://spam"}
        self.assertEqual(self.client.post(reverse("shop:contact"), spam).status_code, 200)
        self.assertEqual(SourcingRequest.objects.count(), 0)

    def test_contact_form_rate_limit(self):
        data = {"name": "Ama", "phone": "0245551234", "item": "one"}
        self.client.post(reverse("shop:contact"), data)
        self.client.post(reverse("shop:contact"), {**data, "item": "two"})
        self.assertEqual(SourcingRequest.objects.count(), 1)

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("024 123 4567"), "233241234567")
        self.assertEqual(normalize_phone("+233 24 123 4567"), "233241234567")
        self.assertEqual(normalize_phone("0086 132 5057 6403"), "8613250576403")

    # --- help page, SEO, error pages
    def test_faq_page_lists_only_active_questions(self):
        FAQ.objects.create(question="How long is delivery?", answer="Four to six weeks.")
        FAQ.objects.create(question="Secret?", answer="No.", is_active=False)
        r = self.client.get(reverse("shop:faq"))
        self.assertContains(r, "How long is delivery?")
        self.assertNotContains(r, "Secret?")

    def test_sitemap_and_robots(self):
        r = self.client.get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn(self.tv.get_absolute_url(), body)
        self.assertNotIn(self.off.get_absolute_url(), body)
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Sitemap:", robots)
        self.assertIn("Disallow: /cart/", robots)

    def test_robots_txt_never_reveals_a_private_admin_address(self):
        with override_settings(ADMIN_URL="admin/"):
            self.assertIn("Disallow: /admin/", self.client.get("/robots.txt").content.decode())
        with override_settings(ADMIN_URL="boski-manage/"):
            robots = self.client.get("/robots.txt").content.decode()
        self.assertNotIn("boski-manage", robots)

    def test_product_page_has_structured_data_and_share_tags(self):
        r = self.client.get(self.tv.get_absolute_url())
        self.assertContains(r, "application/ld+json")
        self.assertContains(r, 'property="og:image"')
        self.assertContains(r, "-25%")

    def test_custom_404_page(self):
        r = self.client.get("/definitely-not-a-page/")
        self.assertEqual(r.status_code, 404)

    def test_admin_new_sections_open(self):
        User = get_user_model()
        User.objects.create_superuser("boski", "b@example.com", "pass12345!")
        self.client.login(username="boski", password="pass12345!")
        SourcingRequest.objects.create(phone="0245551234", item="A tricycle")
        for name in (
            "admin:shop_faq_changelist",
            "admin:shop_sourcingrequest_changelist",
            "admin:shop_faq_add",
        ):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_large_photo_is_shrunk_on_upload(self):
        buf = BytesIO()
        Image.new("RGB", (3600, 2400), (10, 120, 200)).save(buf, "JPEG")
        big = SimpleUploadedFile("big.jpg", buf.getvalue(), content_type="image/jpeg")
        p = Product.objects.create(category=self.cat, name="Big photo", price=5, main_image=big)
        with Image.open(p.main_image.path) as img:
            self.assertLessEqual(max(img.size), 1600)


class PhoneMenuAndAdminRedirectTests(TestCase):
    def test_admin_address_opens_the_dashboard_login(self):
        for url in ("/admin/", "/admin/shop/product/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertEqual(r["Location"], reverse("dashboard:home"))
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("dashboard:login"), r["Location"])

    def test_signed_in_staff_land_on_the_dashboard_from_admin(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_superuser("boss", "b@example.com", "pw-12345-xyz")
        self.client.login(username="boss", password="pw-12345-xyz")
        r = self.client.get("/admin/", follow=True)
        self.assertEqual(r.redirect_chain[-1][0], reverse("dashboard:home"))
        self.assertEqual(r.status_code, 200)

    def test_real_django_admin_moved_away_from_admin_address(self):
        from django.conf import settings

        self.assertNotEqual(settings.ADMIN_URL, "admin/")
        self.assertTrue(reverse("admin:index").startswith("/" + settings.ADMIN_URL))

    def test_every_page_has_the_hamburger_menu(self):
        r = self.client.get("/")
        self.assertContains(r, 'class="mnav"')
        self.assertContains(r, "Shop by category")
