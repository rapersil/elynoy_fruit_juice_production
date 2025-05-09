# beauty_app/context_processors.py

from django.conf import settings

def beauty_settings(request):

    return {
        'settings': {
            'BEAUTY_PARLOR_NAME': settings.BEAUTY_PARLOR_NAME,
            'BEAUTY_PARLOR_ADDRESS': settings.BEAUTY_PARLOR_ADDRESS,
            'BEAUTY_PARLOR_PHONE': settings.BEAUTY_PARLOR_PHONE,
            'BEAUTY_PARLOR_EMAIL': settings.BEAUTY_PARLOR_EMAIL,
            'BEAUTY_PARLOR_OPENING_HOURS': settings.BEAUTY_PARLOR_OPENING_HOURS,
            'BEAUTY_PARLOR_WORKING_DAYS': settings.BEAUTY_PARLOR_WORKING_DAYS,
        }
    }




# def notification_counts(request):
#     """
#     Add notification counts to all template contexts
#     """
#     context = {}
    
#     # Only add the counts if the user is logged in and is staff
#     if request.user.is_authenticated and hasattr(request.user, 'user_type') and request.user.user_type in ['STAFF', 'ADMIN', 'SUPERADMIN']:
#         # Count pending booking requests
#         pending_count = BookingRequest.objects.filter(status='PENDING').count()
#         context['pending_booking_requests_count'] = pending_count
#     else:
#         context['pending_booking_requests_count'] = 0
        
#     return context