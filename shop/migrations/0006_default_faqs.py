from django.db import migrations

DEFAULT_FAQS = [
    (
        "How does preorder work?",
        "Choose a product and tap Preorder on WhatsApp. Your chat with Boski opens with the product "
        "already in the message, and he goes over the price, payment and delivery time with you there.",
    ),
    (
        "How long does delivery take?",
        "Each product page shows an estimated delivery time. Boski confirms the final timing with you "
        "on WhatsApp when you place your preorder.",
    ),
    (
        "How do I pay?",
        "Boski shares the payment details with you in the WhatsApp chat once you confirm your order.",
    ),
    (
        "Can I order something that is not on the website?",
        "Yes. Send a request from the Contact page or message Boski on WhatsApp with a photo or link, "
        "and he will check whether he can source it from China.",
    ),
    (
        "Are the prices final?",
        "The prices on the website are the listed preorder prices. Boski confirms the final amount with "
        "you on WhatsApp before you pay.",
    ),
]


def add_faqs(apps, schema_editor):
    FAQ = apps.get_model("shop", "FAQ")
    if FAQ.objects.exists():
        return
    for i, (q, a) in enumerate(DEFAULT_FAQS):
        FAQ.objects.create(question=q, answer=a, order=i)


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0005_marketplace_models"),
    ]

    operations = [
        migrations.RunPython(add_faqs, migrations.RunPython.noop),
    ]
