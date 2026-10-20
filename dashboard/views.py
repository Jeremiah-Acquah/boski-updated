from datetime import datetime

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from .forms import (
    BannerForm, CategoryForm, FAQForm, ProductForm, ProductImageFormSet,
    RequestForm, SettingsForm, StaffAuthenticationForm,
)
from .views_config import FAQ, Banner, Category, Product, SourcingRequest, StoreSettings

def staff_only(view):
    """Only logged-in staff may open a dashboard page; everyone else goes to the login page."""
    return staff_member_required(view, login_url="dashboard:login")


class DashboardLoginView(LoginView):
    template_name = "dashboard/login.html"
    authentication_form = StaffAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        # Already signed in as admin: skip the form and go straight to the dashboard.
        if request.user.is_authenticated and request.user.is_staff:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_default_redirect_url(self):
        return reverse("dashboard:home")


class DashboardLogoutView(LogoutView):
    next_page = reverse_lazy("shop:home")


# Each entry becomes a sidebar item with a list page and add/edit/delete forms.
# columns: (field or property name, column heading)
SECTIONS = {
    "products": {
        "model": Product, "form": ProductForm, "inline": True,
        "label": "Products", "singular": "product",
        "columns": [("main_image", "Photo"), ("name", "Product"), ("category", "Category"),
                    ("price_display", "Price"), ("is_active", "On website"),
                    ("is_featured", "Featured")],
        "toggles": ["is_active", "is_featured"],
        "search": ["name", "short_description"],
        "fieldsets": [
            ("Product", ["category", "name", "main_image"]),
            ("Details", ["short_description", "description", "delivery_time"]),
            ("Price", ["price", "old_price", "currency"]),
            ("Visibility", ["is_active", "is_featured"]),
        ],
    },
    "categories": {
        "model": Category, "form": CategoryForm,
        "label": "Categories", "singular": "category",
        "columns": [("name", "Name"), ("icon", "Icon"), ("order", "Order")],
        "search": ["name"],
    },
    "banners": {
        "model": Banner, "form": BannerForm,
        "label": "Banners", "singular": "banner",
        "columns": [("image", "Banner"), ("title", "Title"), ("category", "Links to"),
                    ("order", "Order"), ("is_active", "On website")],
        "toggles": ["is_active"],
        "search": ["title"],
    },
    "faqs": {
        "model": FAQ, "form": FAQForm,
        "label": "FAQs", "singular": "FAQ",
        "columns": [("question", "Question"), ("order", "Order"), ("is_active", "On website")],
        "toggles": ["is_active"],
        "search": ["question"],
    },
    "requests": {
        "model": SourcingRequest, "form": RequestForm, "can_create": False,
        "label": "Customer requests", "singular": "request",
        "columns": [("created_at", "Received"), ("name", "Customer"), ("phone", "Phone"),
                    ("item", "Looking for"), ("budget", "Budget"),
                    ("is_handled", "Handled"), ("reply_url", "Reply")],
        "toggles": ["is_handled"],
        "search": ["name", "phone", "item"],
        "pending_filter": "is_handled",
    },
}

SETTINGS_FIELDSETS = [
    ("Store", ["store_name", "tagline", "announcement"]),
    ("WhatsApp", ["whatsapp_number", "whatsapp_display"]),
    ("Contact details", ["email", "location", "working_hours"]),
    ("Social media", ["facebook_url", "instagram_url", "tiktok_url"]),
]


def get_section(key):
    if key not in SECTIONS:
        raise Http404
    return SECTIONS[key]


def base_ctx(active=None):
    return {
        "sections": SECTIONS, "active": active,
        "pending_requests": SourcingRequest.objects.filter(is_handled=False).count(),
    }


def cell(obj, name, toggles=()):
    value = getattr(obj, name, "")
    if callable(value):
        value = value()
    if isinstance(value, bool):
        return {"kind": "toggle" if name in toggles else "bool", "value": value, "field": name}
    if hasattr(value, "storage") and hasattr(value, "name"):  # image/file field
        return {"kind": "image", "value": value.url if value else ""}
    if isinstance(value, datetime):
        return {"kind": "date", "value": value}
    if name.endswith("_url"):
        return {"kind": "link", "value": value}
    text = "" if value is None else str(value)
    if len(text) > 70:
        text = text[:70] + "…"
    return {"kind": "text", "value": text or "-"}


def layout(form, fieldsets):
    if not fieldsets:
        return [(None, list(form))]
    return [(title, [form[n] for n in names]) for title, names in fieldsets]


def safe_next(request, fallback):
    nxt = request.POST.get("next", "")
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else fallback


@staff_only
def home(request):
    cards = []
    for key, cfg in SECTIONS.items():
        qs = cfg["model"].objects.all()
        live_field = next((f for f, _ in cfg["columns"] if f in ("is_active",)), None)
        cards.append({
            "key": key, "label": cfg["label"], "total": qs.count(),
            "live": qs.filter(**{live_field: True}).count() if live_field else None,
        })
    waiting = SourcingRequest.objects.filter(is_handled=False).order_by("-created_at")[:5]
    return render(request, "dashboard/home.html", {
        **base_ctx("home"), "cards": cards, "waiting": waiting,
        "featured": Product.objects.filter(is_featured=True).count(),
    })


@staff_only
def item_list(request, section):
    cfg = get_section(section)
    qs = cfg["model"].objects.all()
    q = request.GET.get("q", "").strip()
    pending = bool(request.GET.get("pending")) and "pending_filter" in cfg
    if q:
        cond = Q()
        for f in cfg["search"]:
            cond |= Q(**{f"{f}__icontains": q})
        qs = qs.filter(cond)
    if pending:
        qs = qs.filter(**{cfg["pending_filter"]: False})

    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    toggles = cfg.get("toggles", [])
    rows = []
    for obj in page.object_list:
        cells = [cell(obj, name, toggles) for name, _ in cfg["columns"]]
        first_text = next((c for c in cells if c["kind"] == "text"), None)
        if first_text:
            first_text["link"] = True
        rows.append({"obj": obj, "cells": cells})

    return render(request, "dashboard/list.html", {
        **base_ctx(section), "cfg": cfg, "key": section, "page": page, "rows": rows,
        "headers": [h for _, h in cfg["columns"]], "q": q, "pending": pending,
        "can_create": cfg.get("can_create", True),
    })


@staff_only
def item_edit(request, section, pk=None):
    cfg = get_section(section)
    if pk is None and cfg.get("can_create") is False:
        raise Http404
    instance = get_object_or_404(cfg["model"], pk=pk) if pk else None
    form = cfg["form"](request.POST or None, request.FILES or None, instance=instance)
    formset = None
    if cfg.get("inline"):
        formset = ProductImageFormSet(request.POST or None, request.FILES or None,
                                      instance=form.instance)
    if request.method == "POST" and form.is_valid() and (formset is None or formset.is_valid()):
        saved = form.save()
        if formset is not None:
            formset.instance = saved
            formset.save()
        messages.success(request, f"Saved {cfg['singular']}.")
        return redirect("dashboard:list", section=section)
    return render(request, "dashboard/form.html", {
        **base_ctx(section), "cfg": cfg, "key": section, "form": form, "formset": formset,
        "instance": instance, "title": cfg["label"],
        "groups": layout(form, cfg.get("fieldsets")),
        "back_url": reverse("dashboard:list", args=[section]),
    })


@staff_only
def store_settings(request):
    instance = StoreSettings.objects.first()
    form = SettingsForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Saved store settings.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/form.html", {
        **base_ctx("settings"), "cfg": {"singular": "settings"}, "form": form, "formset": None,
        "instance": None, "title": "Store settings", "singleton": True,
        "groups": layout(form, SETTINGS_FIELDSETS),
    })


@staff_only
@require_POST
def item_toggle(request, section, pk, field):
    cfg = get_section(section)
    if field not in cfg.get("toggles", []):
        raise Http404
    obj = get_object_or_404(cfg["model"], pk=pk)
    setattr(obj, field, not getattr(obj, field))
    obj.save(update_fields=[field])
    return redirect(safe_next(request, "/"))


@staff_only
def item_delete(request, section, pk):
    cfg = get_section(section)
    obj = get_object_or_404(cfg["model"], pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, f"Deleted {cfg['singular']}.")
        return redirect("dashboard:list", section=section)
    return render(request, "dashboard/confirm_delete.html", {
        **base_ctx(section), "cfg": cfg, "key": section, "obj": obj,
    })
