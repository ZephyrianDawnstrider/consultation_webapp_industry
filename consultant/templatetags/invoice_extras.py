from django import template

register = template.Library()

@register.filter(name='snake_case_to_title')
def snake_case_to_title(value):
    """
    Converts snake_case string to Title Case string.
    Example: 'awaiting_review' -> 'Awaiting Review'
    """
    if not isinstance(value, str):
        return value
    return value.replace('_', ' ').title()
