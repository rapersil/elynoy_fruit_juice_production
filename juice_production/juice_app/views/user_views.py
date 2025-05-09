from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from ..models import UserProfile

@login_required
def user_profile(request):
    """View user profile."""
    user = request.user
    profile = user.profile
    
    return render(request, 'juice_app/auth/profile.html', {
        'user': user,
        'profile': profile
    })