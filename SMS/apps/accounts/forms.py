"""Forms for authentication and password management."""
from django import forms
from django.contrib.auth import password_validation


class LoginForm(forms.Form):
    school_code = forms.SlugField(
        max_length=30,
        required=False,
        label="School code",
        help_text="Leave blank only if you are a Super Admin.",
        widget=forms.TextInput(attrs={"autofocus": False, "placeholder": "e.g. stmarys"}),
    )
    username = forms.CharField(
        max_length=150, label="Username / admission number",
        widget=forms.TextInput(attrs={"autofocus": True}),
    )
    password = forms.CharField(widget=forms.PasswordInput)


class ForceChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Temporary / current password", widget=forms.PasswordInput
    )
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirm new password", widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if self.user is None or not self.user.check_password(password):
            raise forms.ValidationError("Your current password is incorrect.")
        return password

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        confirm_password = cleaned.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error("confirm_password", "The two password fields do not match.")
        if new_password and self.user is not None:
            password_validation.validate_password(new_password, self.user)
        return cleaned


class ForgotPasswordForm(forms.Form):
    username = forms.CharField(max_length=150, label="Username / admission number")


class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirm new password", widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        confirm_password = cleaned.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error("confirm_password", "The two password fields do not match.")
        if new_password and self.user is not None:
            password_validation.validate_password(new_password, self.user)
        return cleaned
