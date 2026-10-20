from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.DashboardLoginView.as_view(), name="login"),
    path("logout/", views.DashboardLogoutView.as_view(), name="logout"),
    path("settings/", views.store_settings, name="settings"),
    path("<str:section>/", views.item_list, name="list"),
    path("<str:section>/new/", views.item_edit, name="create"),
    path("<str:section>/<int:pk>/edit/", views.item_edit, name="edit"),
    path("<str:section>/<int:pk>/delete/", views.item_delete, name="delete"),
    path("<str:section>/<int:pk>/toggle/<str:field>/", views.item_toggle, name="toggle"),
]
