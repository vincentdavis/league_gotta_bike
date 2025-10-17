"""Views for user account management."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.membership.models import Membership

from .forms import UserProfileForm


@login_required
def profile(request):
    """Display and edit user profile.

    Shows user information with edit form and list of organization memberships.
    Only accessible by the authenticated user for their own profile.
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    # Get user's memberships with related organization data
    memberships = Membership.objects.filter(
        user=request.user
    ).select_related(
        'organization',
        'organization__parent'
    ).order_by('-modified_date')

    context = {
        'form': form,
        'memberships': memberships,
    }

    return render(request, 'accounts/profile.html', context)
