from django.db import models
from django.contrib.auth.models import User
import os



class Client(models.Model):

    id = models.AutoField(primary_key=True)  # Otomatik artan ve unique id
    tc = models.CharField(max_length=11)  # T.C. Kimlik No
    name = models.CharField(max_length=50)  # Ad
    surname = models.CharField(max_length=50)  # Soyad
    address = models.TextField()  # Adres
    phone = models.CharField(max_length=15)  # Telefon
    email = models.EmailField(blank=True , null=True )  # Mail
    agreement_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Yeni davanın anlaşma bedeli
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)  # Alınan para
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2)  # Kalan bakiye
    file_expenses = models.DecimalField(max_digits=10, decimal_places=2)  # Dosya masrafları
    last_sms_date = models.DateField(null=True, blank=True)  # En son SMS atma tarihi
    files = models.TextField()  # Müvekkilin dosyaları
    
    created_at = models.DateTimeField(auto_now_add=True)  # Oluşturulma tarihi
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User tracking
    updated_at = models.DateTimeField(auto_now=True)  # Güncellenme tarihi
    notes = models.TextField(blank=True, null=True)  # Notlar

    def __str__(self):
        return f"{self.tc}-{self.name} {self.surname}"



class Case(models.Model):

    id = models.AutoField(primary_key=True)  # Otomatik artan ve unique id
    client = models.ForeignKey(Client, on_delete=models.CASCADE, blank=True,null=True )  # Müvekkil ile ilişki
    case_number = models.CharField(max_length=50)  # Dava numarası
    case_type = models.CharField(max_length=30,null=True,blank=True)                 # Dava türü
    status = models.CharField(max_length=20)                    # Dava durumu
    court = models.CharField(max_length=100)                    # Mahkeme
    description = models.TextField(blank=True, null=True)       # Dava açıklaması
    
    created_at = models.DateTimeField(auto_now_add=True)        # Oluşturulma tarihi
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User tracking
    updated_at = models.DateTimeField(auto_now=True)            # Güncellenme tarihi
    case_file = models.FileField(upload_to='case_files/', blank=True, null=True)  # File upload

    def __str__(self):
        return f"{self.case_number} - {self.client}"
    
class CaseProgress(models.Model):
    case = models.ForeignKey(Case, related_name='progress_steps', on_delete=models.CASCADE)  # Davaya bağlı adımlar
    description = models.TextField(blank=True, null=True)  # Açıklama
    unique_info = models.TextField(max_length=100, blank=True, null=True)  # Özel bilgi
    type = models.CharField(max_length=50)  # Adım türü
    progress_date = models.DateTimeField()  # İlerleme tarihi
    created_at = models.DateTimeField(auto_now_add=True)  # Oluşturulma tarihi
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User tracking

class ActionList(models.Model):
    caseprogress = models.ForeignKey(CaseProgress, related_name="actions", on_delete=models.CASCADE)
    action_description = models.TextField(blank=True, null=True)
    action_deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
class ProcessTypes(models.Model):
    id = models.AutoField(primary_key=True)  # Otomatik artan ve unique id
    file_type = models.CharField(max_length=50)
    process_type = models.CharField(max_length=100, unique=True)
    deadline = models.IntegerField()
    priority = models.IntegerField()
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.process_type


def get_upload_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    folder_name = {
        'pdf': 'uploads/pdf_files',
        'xls': 'uploads/excel_files',
        'xlsx': 'uploads/excel_files',
        # Diğer uzantılar burada tanımlanabilir
    }.get(ext, 'uploads/other_files')
    return os.path.join(folder_name, filename)

class DailyFile(models.Model):
    id = models.AutoField(primary_key=True)  # Otomatik artan ve unique id
    file = models.FileField(upload_to="uploads/daily_files",unique=True)
    file_type = models.CharField(max_length=50,blank=True,null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User tracking
    def __str__(self):
        return self.file.name
    
class UploadedFile(models.Model):
    from Client.models import Case
    id = models.AutoField(primary_key=True)  # Otomatik artan ve unique id
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_upload_path, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User tracking
    def __str__(self):
        return self.file.name
    

class Notification(models.Model):

    id = models.AutoField(primary_key=True)  # Unique identifier
    text = models.TextField()  # Notification text
    priority = models.IntegerField()  # Priority level as a numeric value (1, 2, 3)
    link = models.URLField()  # Link associated with the notification
    read = models.BooleanField(default=False)  # Read status
    deadline_date = models.DateField(blank=True, null=True)  # Deadline date
    created_at = models.DateTimeField(auto_now_add=True)  # Creation timestamp
    last_action_date = models.DateTimeField(auto_now=True)  # Last action timestamp
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User tracking
    class Meta:
        db_table = 'notification'
        ordering = ['-priority', 'read', '-created_at']  # Ordering by priority, read status, and created date

    def __str__(self):
        return f"{self.text} - {self.priority}"
 
class Note(models.Model):
    id = models.AutoField(primary_key=True)  # Otomatik artan ve unique id
    case = models.ForeignKey(Case, related_name='case_notes', on_delete=models.CASCADE)  # Davaya bağlı adımlar
    text = models.TextField()  # Not
    created_at = models.DateTimeField(auto_now_add=True)  # Oluşturulma tarihi
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User tracking
    updated_at = models.DateTimeField(auto_now=True)  # Güncellenme tarihi
    class Meta:
        ordering = ['-created_at']  # Ordering by creation date

    def __str__(self):
        return f"{self.note[:50]}-{self.updated_at}"

   

