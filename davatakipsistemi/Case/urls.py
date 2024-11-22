from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('',views.add_case, name='case'),
    path('add_case/',views.add_case, name='add_case'),
    path("<int:id>", views.show_case_detail,name='show_case_detail'),
    path('case_list/', views.show_case_list, name='case_list'),
    path('<int:case_id>/remove-client/', views.remove_client_from_case, name='remove_client_from_case'),
    # path('', login_required(views.case, login_url='/auth/login/'), name='case'),
]
