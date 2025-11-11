from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Filtro de template que adiciona uma classe CSS
    a um campo de formulário do Django.
    """
    return field.as_widget(attrs={'class': css_class})
