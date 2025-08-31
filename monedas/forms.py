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
    class Meta:
        model = Moneda
        fields = [
            "codigo",
            "nombre",
            "simbolo",
            "decimales",
            "minima_denominacion",
            "admite_en_linea",
            "admite_terminal",
        ]
        widgets = {
            "codigo": forms.Select(choices=CHOICES, attrs={
                "class": "w-full px-3 py-2 border rounded-lg border-gray-300 focus:ring-[var(--brand)] focus:border-[var(--brand)]"
            }),
            "nombre": forms.TextInput(attrs={
                "readonly": True,
                "class": "w-full px-3 py-2 border rounded-lg bg-gray-100 border-gray-300"
            }),
            "simbolo": forms.TextInput(attrs={
                "readonly": True,
                "class": "w-full px-3 py-2 border rounded-lg bg-gray-100 border-gray-300"
            }),
            "decimales": forms.NumberInput(attrs={
                "min": 0,
                "max": 6,
                "step": 1,
                "class": "w-full px-3 py-2 border rounded-lg border-gray-300 focus:ring-[var(--brand)] focus:border-[var(--brand)]"
            }),
            "minima_denominacion": forms.NumberInput(attrs={
                "min": 1,
                "step": 1,
                "class": "w-full px-3 py-2 border rounded-lg border-gray-300 focus:ring-[var(--brand)] focus:border-[var(--brand)]"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Autocompletar nombre y símbolo si hay código seleccionado
        code = None
        if self.is_bound:
            code = self.data.get(self.add_prefix("codigo")) or self.data.get("codigo")
        elif self.instance and getattr(self.instance, "codigo", None):
            code = self.instance.codigo

        if code in CURRENCIES:
            d = CURRENCIES[code]
            self.initial.setdefault("nombre", d["name"])
            self.initial.setdefault("simbolo", d["symbol"])

    def clean_minima_denominacion(self):
        """Validar que sea un entero positivo"""
        value = self.cleaned_data.get("minima_denominacion")
        if value is None or value < 1:
            raise forms.ValidationError("La mínima denominación debe ser un número entero positivo.")
        return value

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
