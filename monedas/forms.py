from django import forms
from .models import Moneda

# Catálogo ISO 4217 con nombre, símbolo y emoji (bandera)
CURRENCIES = {
    "USD": {"name": "Dólar estadounidense", "symbol": "$",  "emoji": "🇺🇸"},
    "EUR": {"name": "Euro",                  "symbol": "€",  "emoji": "🇪🇺"},
    "ARS": {"name": "Peso argentino",        "symbol": "$",  "emoji": "🇦🇷"},
    "BRL": {"name": "Real brasileño",        "symbol": "R$", "emoji": "🇧🇷"},
    "CLP": {"name": "Peso chileno",          "symbol": "$",  "emoji": "🇨🇱"},
    "COP": {"name": "Peso colombiano",       "symbol": "$",  "emoji": "🇨🇴"},
    "MXN": {"name": "Peso mexicano",         "symbol": "$",  "emoji": "🇲🇽"},
    "PEN": {"name": "Sol peruano",           "symbol": "S/", "emoji": "🇵🇪"},
    "PYG": {"name": "Guaraní paraguayo",     "symbol": "₲",  "emoji": "🇵🇾"},
    "UYU": {"name": "Peso uruguayo",         "symbol": "$",  "emoji": "🇺🇾"},
    "GBP": {"name": "Libra esterlina",       "symbol": "£",  "emoji": "🇬🇧"},
    "JPY": {"name": "Yen japonés",           "symbol": "¥",  "emoji": "🇯🇵"},
    "CNY": {"name": "Yuan chino",            "symbol": "¥",  "emoji": "🇨🇳"},
    "AUD": {"name": "Dólar australiano",     "symbol": "$",  "emoji": "🇦🇺"},
    "CAD": {"name": "Dólar canadiense",      "symbol": "$",  "emoji": "🇨🇦"},
    "CHF": {"name": "Franco suizo",          "symbol": "Fr", "emoji": "🇨🇭"},
}

def _choice_label(code: str) -> str:
    d = CURRENCIES[code]
    return f"{d['emoji']} {code} — {d['name']}"

CHOICES = [(code, _choice_label(code)) for code in CURRENCIES.keys()]


class MonedaForm(forms.ModelForm):
    """
    - 'codigo' es un <select> con emoji.
    - 'nombre' y 'simbolo' se autocompletan y se muestran deshabilitados.
    """
    codigo = forms.ChoiceField(choices=CHOICES, label="Código")
    nombre = forms.CharField(label="Nombre", required=False, disabled=True)
    simbolo = forms.CharField(label="Símbolo", required=False, disabled=True)

    class Meta:
        model = Moneda
        fields = ["codigo", "nombre", "simbolo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        code = None
        if self.is_bound:
            code = self.data.get(self.add_prefix("codigo")) or self.data.get("codigo")
        elif self.instance and getattr(self.instance, "codigo", None):
            code = self.instance.codigo

        if code in CURRENCIES:
            d = CURRENCIES[code]
            self.initial.setdefault("nombre", d["name"])
            self.initial.setdefault("simbolo", d["symbol"])

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("codigo")
        if code in CURRENCIES:
            d = CURRENCIES[code]
            cleaned["nombre"] = d["name"]
            cleaned["simbolo"] = d["symbol"]
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        code = self.cleaned_data.get("codigo")
        if code in CURRENCIES:
            d = CURRENCIES[code]
            instance.codigo = code
            instance.nombre = d["name"]
            instance.simbolo = d["symbol"]
        if commit:
            instance.save()
        return instance
