import datetime
from django.utils.timezone import now
from datetime import timedelta

class TrackUserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user = request.user
            # Log the current request time
            current_time = now()

            # Check the last activity time
            if hasattr(user, 'last_activity_time') and user.last_activity_time:
                # Calculate idle duration since the last request
                idle_time = current_time - user.last_activity_time
                if idle_time < timedelta(minutes=30):  # Consider only sessions with short idle times
                    user.total_active_time += idle_time

            # Update the last activity time
            user.last_activity_time = current_time
            user.save(update_fields=['total_active_time', 'last_activity_time'])
        
        response = self.get_response(request)
        return response
