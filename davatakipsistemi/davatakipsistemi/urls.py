"""davatakipsistemi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required

from django.urls import path
# http://127.0.0.1:8000/ => anasayfa
# http://127.0.0.1:8000/index => anasayfa
# http://127.0.0.1:8000/muvekkildetay/1 => 1. müvekkil 
# bebeğim buraya uploadı neden eklemedin aşkm
# http://127.0.0.1:8000/notifications/ => bildirim paneli
# http://127.0.0.1:8000/client/ => client paneli
# http://127.0.0.1:8000/case/ => case paneli
# http://127.0.0.1:8000/auth/login => login ekranı


urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/',include('account.urls')),
    path('',include('anasayfa.urls')),
    path('upload/', include('fileIO.urls')),
    path('notifications/', include('notifications.urls')),
    path('client/', include('Client.urls')),
    path('case/', include('Case.urls')),
    path('account/', include('account.urls')),
    path('api/', include('api.urls')),
]
