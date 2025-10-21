"""Mixins for organization views."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class UserNameRequiredMixin:
    """Mixin to ensure user has first and last name before proceeding.

    This mixin checks that authenticated users have filled out their
    first_name and last_name fields before allowing them to create
    or join organizations.
    """

    def dispatch(self, request, *args, **kwargs):
        """Check if user has first and last name before allowing action."""
        if request.user.is_authenticated:
            if not request.user.first_name or not request.user.last_name:
                messages.warning(
                    request,
                    'Please complete your profile by adding your first and last name '
                    'before creating or joining organizations.'
                )
                return redirect(reverse('accounts:profile'))

        return super().dispatch(request, *args, **kwargs)
