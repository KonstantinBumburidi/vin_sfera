from django import template

register = template.Library()


@register.filter
def is_in(value, collection):
    return value in collection