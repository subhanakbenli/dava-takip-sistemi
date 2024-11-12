from django.shortcuts import render
from django.http import JsonResponse
from Client.models import Notification

# Create your views here.

def get_notifications(request):
    # Fetch notifications from the database
    notifications = Notification.objects.all().filter(read = False)
    
    # Serialize notifications
    notifications_data = [
        {
            'id': notification.id,
            'message': notification.text,
            'url': notification.link,
            'is_read': notification.read,
            'priority': notification.priority,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for notification in notifications
    ]
    return JsonResponse(notifications_data, safe=False)

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone  # Add this import
import json
from Client.models import Notification
from django.views.decorators.csrf import csrf_exempt


@require_POST
@login_required
@csrf_exempt
def mark_notifications_read(request):
    try:
        notification_ids = json.loads(request.POST.get('notification_ids', '[]'))
        
        if not notification_ids:
            return JsonResponse({'success': False, 'error': 'No notifications selected'})
        
        # Update the notifications
        Notification.objects.filter(
            id__in=notification_ids,
            read=False  # Only update unread notifications
        ).update(
            read=True,
            last_action_date=timezone.now()
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

