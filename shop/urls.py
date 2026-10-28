from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="products"),
    path("categories/", views.category_list, name="categories"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    path("product/<slug:slug>/", views.product_detail, name="product"),
    path("search/", views.search, name="search"),
    # preorder list (cart)
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    # wishlist
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<int:pk>/", views.wishlist_toggle, name="wishlist_toggle"),
    # info pages
    # info pages
    path("help/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("about/", views.about, name="about"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("terms/", views.terms, name="terms"),
    path("robots.txt", views.robots_txt, name="robots"),
]
