from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import AppUser, CustomUser

@receiver(post_delete, sender=AppUser)
def cleanup_orphaned_custom_user(sender, instance, **kwargs):
    """
    Signal handler to clean up CustomUser instances that have no remaining AppUser associations.
    This runs after an AppUser is deleted and checks if the associated CustomUser has any
    remaining AppUser entries. If not, the CustomUser is deleted.
    """
    try:
        custom_user = instance.user
        # Check if this CustomUser has any remaining AppUser associations
        if not AppUser.objects.filter(user_id=custom_user.id).exists():
            custom_user.delete()
    except CustomUser.DoesNotExist:
        # CustomUser was already deleted
        pass 