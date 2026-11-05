from django import template

from base.site_menu import ROW_1, ROW_2, build_row

register = template.Library()


@register.simple_tag(takes_context=True)
def site_menu(context):
    """{% site_menu as menu %} → menu.row_1, menu.row_2 (данные в base/site_menu.py)."""
    request = context.get("request")
    path = request.path if request else ""
    return {"row_1": build_row(ROW_1, path), "row_2": build_row(ROW_2, path)}
