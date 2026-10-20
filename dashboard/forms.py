from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.text import slugify

from .views_config import (
    FAQ, Banner, Category, Product, ProductImage, SourcingRequest, StoreSettings,
)


class AutoSlugMixin:
    """Boski never sees the slug; it is created from the name and kept unique."""

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.slug:
            base = slugify(obj.name) or "item"
            slug, n = base, 2
            while type(obj).objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            obj.slug = slug
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class ProductForm(AutoSlugMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "main_image", "short_description", "description",
                  "delivery_time", "price", "old_price", "currency", "is_active", "is_featured"]
        widgets = {"description": forms.Textarea(attrs={"rows": 6}),
                   "short_description": forms.Textarea(attrs={"rows": 2})}


class CategoryForm(AutoSlugMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "icon", "order"]


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = "__all__"


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = "__all__"
        widgets = {"answer": forms.Textarea(attrs={"rows": 5})}


class RequestForm(forms.ModelForm):
    class Meta:
        model = SourcingRequest
        fields = "__all__"


class SettingsForm(forms.ModelForm):
    class Meta:
        model = StoreSettings
        fields = "__all__"


ProductImageFormSet = forms.inlineformset_factory(
    Product, ProductImage, fields=("image", "caption", "order"), extra=3, can_delete=True,
)


class StaffAuthenticationForm(AuthenticationForm):
    """Login form that only lets staff (admin) accounts into the dashboard."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "no_access": "This account does not have access to the dashboard.",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)  # blocks inactive accounts
        if not user.is_staff:
            raise forms.ValidationError(self.error_messages["no_access"], code="no_access")
