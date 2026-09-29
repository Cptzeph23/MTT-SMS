"""Password reset token generation.

Wraps Django's default token generator, which already invalidates a token
once the user's password or last_login changes. No custom secret handling
is needed.
"""
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import User


def make_reset_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    from django.urls import reverse

    path = reverse("accounts:reset-password-confirm", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


def user_from_uidb64(uidb64):
    try:
        pk = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=pk)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


def token_is_valid(user, token):
    return user is not None and default_token_generator.check_token(user, token)
