from django import template

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    """Añade clases CSS al widget del campo sin pisar las existentes."""
    attrs = field.field.widget.attrs.copy()
    existing = attrs.get("class", "")
    attrs["class"] = f"{existing} {css}".strip() if existing else css
    return field.as_widget(attrs=attrs)
