from django.urls import path
from .views import upload_page, upload_file

urlpatterns = [
    path('daily', upload_page, name='upload_page'),  # Yükleme sayfası için URL
    path('upload', upload_file, name='upload_file'),  # Dosya yüklemek için URL

]