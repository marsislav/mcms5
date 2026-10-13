"""
users.forms - forms of the account pages (all get Bootstrap's ``form-control`` class).

``RegisterForm``  sign-up: username + e-mail + password twice. The e-mail is REQUIRED and unique
                  (case-insensitive) because "forgot password" sends the reset link to it.
``ProfileForm``   "My profile": display name, photo, short description, location, website.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (AuthenticationForm, PasswordResetForm, SetPasswordForm,
                                       UserCreationForm)

from .models import Profile


class StyledMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class LoginForm(StyledMixin, AuthenticationForm):
    pass


class ResetRequestForm(StyledMixin, PasswordResetForm):
    pass


class NewPasswordForm(StyledMixin, SetPasswordForm):
    pass


class RegisterForm(StyledMixin, UserCreationForm):
    email = forms.EmailField(required=True, help_text='Needed to reset a forgotten password. Never shown publicly.')

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this e-mail already exists.')
        return email


class ProfileForm(StyledMixin, forms.ModelForm):
    """Edit the public profile. The photo can be replaced or removed ("Clear" checkbox)."""

    class Meta:
        model = Profile
        fields = ('display_name', 'avatar', 'bio', 'location', 'website')
        widgets = {'bio': forms.Textarea(attrs={'rows': 5, 'maxlength': 500})}
