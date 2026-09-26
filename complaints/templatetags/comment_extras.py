from django import template

register = template.Library()


@register.filter
def top_level(comments):
    """Filters a comment queryset down to top-level comments only, oldest first.
    Needed for pages that loop over many complaints at once (like Community),
    where each complaint's thread must be filtered inline in the template."""
    return comments.filter(parent__isnull=True).order_by('created_at')