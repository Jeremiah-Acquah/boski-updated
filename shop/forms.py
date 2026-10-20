from django import forms

from .models import SourcingRequest


class SourcingRequestForm(forms.ModelForm):
    # Hidden field that real visitors never fill in; bots usually do.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = SourcingRequest
        fields = ["name", "phone", "item", "budget"]
        labels = {
            "name": "Your name",
            "phone": "Your WhatsApp number",
            "item": "What do you want Boski to find?",
            "budget": "Budget (optional)",
        }
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel", "placeholder": "024 123 4567"}),
            "item": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Example: 2023 Toyota Hilux, white, automatic. Or paste a link."}
            ),
            "budget": forms.TextInput(attrs={"placeholder": "Example: GH₵ 300,000"}),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) < 9:
            raise forms.ValidationError("Enter a phone number with at least 9 digits.")
        return phone

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
