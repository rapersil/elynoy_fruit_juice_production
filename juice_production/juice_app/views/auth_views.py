from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView, DetailView, FormView
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.views import (
    PasswordChangeView, 
    PasswordResetView,
    PasswordResetConfirmView
)
from django.contrib.auth.tokens import default_token_generator
from django import forms
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from juice_app.models import UserProfile
from ..forms import (
    UserLoginForm,
    UserRegistrationForm,
    UserProfileForm,
    UserUpdateForm
)

def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Get the URL to redirect to after login
                next_url = request.GET.get('next', 'dashboard')
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'juice_app/auth/login.html', {'form': form})

def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

def register_view(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create User
            user = form.save(commit=False)
            user.set_password(form.cleaned_data.get('password1'))
            user.save()
            
            # Create UserProfile
            UserProfile.objects.create(
                user=user,
                role='staff',  # Default role for new users
                phone=form.cleaned_data.get('phone', ''),
                department=form.cleaned_data.get('department', '')
            )
            
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'juice_app/auth/register.html', {'form': form})



@login_required
def edit_profile_view(request):
    """Edit user profile."""
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('user_profile')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = UserProfileForm(instance=profile)
    
    return render(request, 'juice_app/auth/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })



@login_required
def user_list_view(request):
    """List users (admin only)."""
    if not request.user.profile.role in ['admin', 'superadmin']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    users = User.objects.all().order_by('username')
    return render(request, 'juice_app/auth/user_list.html', {'users': users})

@login_required
def user_detail_view(request, user_id):
    """View user details (admin only)."""
    if not request.user.profile.role in ['admin', 'superadmin']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id)
    return render(request, 'juice_app/auth/user_detail.html', {'user': user})

@login_required
def toggle_user_status(request, user_id):
    """Toggle user active status (admin only)."""
    if not request.user.profile.role in ['admin', 'superadmin']:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent disabling your own account
    if user == request.user:
        messages.error(request, 'You cannot disable your own account.')
        return redirect('user_list')
    
    # Toggle status
    user.is_active = not user.is_active
    user.save()
    
    action = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} has been {action}.')
    return redirect('user_list')

@login_required
def change_user_role(request, user_id):
    """Change user role (superadmin only)."""
    if not request.user.profile.role == 'superadmin':
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in ['staff', 'admin', 'superadmin']:
            # Prevent changing your own role from superadmin
            if user == request.user and new_role != 'superadmin':
                messages.error(request, 'You cannot change your own superadmin role.')
                return redirect('user_detail', user_id=user_id)
            
            profile.role = new_role
            profile.save()
            messages.success(request, f'Role for {user.username} changed to {new_role}.')
            return redirect('user_detail', user_id=user_id)
    
    return render(request, 'juice_app/auth/change_role.html', {'user': user})




class CustomPasswordChangeView(PasswordChangeView):
    """Custom password change view."""
    template_name = 'juice_app/auth/change_password.html'
    success_url = reverse_lazy('profile')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully!')
        return super().form_valid(form)

class PasswordResetRequestView(FormView):
    """View for requesting a password reset without email."""
    template_name = 'juice_app/auth/password_reset.html'
    form_class = forms.Form
    success_url = reverse_lazy('login')
    
    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        
        class UsernameForm(forms.Form):
            username = forms.CharField(
                widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
            )
            
        return UsernameForm(**self.get_form_kwargs())
    
    def form_valid(self, form):
        username = form.cleaned_data['username']
        try:
            user = User.objects.get(username=username)
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Redirect to the password reset confirmation page
            reset_url = reverse_lazy('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            messages.info(self.request, f'Password reset initiated for {username}')
            return redirect(reset_url)
        except User.DoesNotExist:
            messages.error(self.request, 'Username not found.')
            return redirect('password_reset')
        
        return super().form_valid(form)

class CustomPasswordResetConfirmView(FormView):
    """Custom password reset confirmation view (in-app)."""
    template_name = 'juice_app/auth/password_reset_confirm.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('login')
    
    def get_user(self, uidb64):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        return user
    
    def get(self, request, *args, **kwargs):
        user = self.get_user(kwargs['uidb64'])
        token = kwargs['token']
        
        if user is not None and default_token_generator.check_token(user, token):
            return super().get(request, *args, **kwargs)
        else:
            messages.error(request, 'The password reset link is invalid or has expired.')
            return redirect('login')
    
    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
            
        user = self.get_user(self.kwargs['uidb64'])
        return form_class(user, **self.get_form_kwargs())
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Your password has been reset successfully! Please log in.')
        return super().form_valid(form)

# For admin-initiated password reset
@login_required
def admin_reset_user_password(request, user_id):
    """Reset a user's password (admin only)."""
    if not request.user.profile.role in ['admin', 'superadmin']:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Password for {user.username} has been reset successfully.')
            return redirect('user_detail', user_id=user_id)
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'juice_app/auth/admin_reset_password.html', {
        'form': form,
        'target_user': user
    })