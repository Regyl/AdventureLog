# your_app/adapters.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class CustomAccountAdapter(DefaultAccountAdapter):
    """Control regular signup based on DISABLE_REGISTRATION setting"""
    
    def is_open_for_signup(self, request):
        """
        Determines if regular signup is allowed.
        Check DISABLE_REGISTRATION env variable.
        """
        return settings.DISABLE_REGISTRATION is False


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Control social signup based on SOCIALACCOUNT_ALLOW_SIGNUP setting"""
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Determines if social signup is allowed.
        Check SOCIALACCOUNT_ALLOW_SIGNUP env variable.
        
        Returning False shows the same 'signup_closed.html' template
        as regular signup, but only blocks NEW social signups.
        Existing users can still log in.
        """
        # If social signup is disabled, only allow existing users
        if not settings.SOCIALACCOUNT_ALLOW_SIGNUP:
            return sociallogin.is_existing
        
        return True
