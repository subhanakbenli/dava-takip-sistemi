from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required


urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    # path('', login_required(views.notification_list, login_url='/auth/login/'), name='notification_list'),
    path('notifications/delete/<int:id>/', views.notification_delete, name='notification_delete'),
    path('work_list/', views.show_work_list, name='work_list'),
    path('notifications/mark_as_read/', views.mark_notifications_as_read, name='mark_notifications_as_read'),
    path('work_list/download/', views.download_work_list_pdf, name='download_work_list_pdf'),
    path('action_list/', views.show_action_list, name='action_list'),
    path('add_note/', views.add_note, name='add_note'),
]
