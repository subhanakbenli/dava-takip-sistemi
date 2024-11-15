from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', views.add_client, name='client'),
    path('add_client/', views.add_client, name='add_client'),
    path("<int:id>", views.show_client_detail,name='show_client_detail'),
    path("client_list/", views.show_client_list, name="client_list"),
    path("<int:id>/edit_client/", views.edit_client, name="edit_client"),
    path('client/<int:client_id>/download/docx/', views.download_client_docx, name='download_client_docx'),
    path('client/<int:client_id>/download/pdf/', views.download_client_pdf, name='download_client_pdf'),
    # path('', login_required(views.client, login_url='/auth/login/'), name='client'),
    # path('addclient/', login_required(views.muvekkilEkle, login_url='/auth/login/'), name='muvekkilekle'),
]
