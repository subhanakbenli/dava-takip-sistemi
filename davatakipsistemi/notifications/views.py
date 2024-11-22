from Client.models import Notification, CaseProgress # Bildirim modelinin yolu
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import datetime, date, timedelta
from django.db.models import F
from django.contrib.auth.decorators import login_required

def add_notification():

    # Örnek bildirim verileri ekle
    Notification.objects.create(
        text='Yeni bir dava kaydedildi: "Örnek Davası".',
        priority=3,  # Yüksek öncelik
        link='https://example.com/dava/1',
    )

    Notification.objects.create(
        text='Davaya itiraz edildi: "Örnek Davası".',
        priority=2,  # Orta öncelik
        link='https://example.com/dava/1/itiraz',
    )

    Notification.objects.create(
        text='Dava duruşması tarihi belirlendi: "Örnek Davası", 15 Kasım 2024.',
        priority=3,  # Yüksek öncelik
        link='https://example.com/dava/1/durusma',
    )

    Notification.objects.create(
        text='Müşteri ile toplantı planlandı: "Örnek Davası".',
        priority=1,  # Düşük öncelik
        link='https://example.com/dava/1/toplanti',
    )

    Notification.objects.create(
        text='Davadan geri çekilme talebi alındı: "Örnek Davası".',
        priority=2,  # Orta öncelik
        link='https://example.com/dava/1/geri-cekilme',
    )

    Notification.objects.create(
        text='Dava dosyası güncellendi: "Örnek Davası".',
        priority=1,  # Düşük öncelik
        link='https://example.com/dava/1/dosyaguncelleme',
    )

    Notification.objects.create(
        text='Mahkeme kararı çıktı: "Örnek Davası".',
        priority=3,  # Yüksek öncelik
        link='https://example.com/dava/1/mahkeme-karari',
    )

    Notification.objects.create(
        text='Yeni kanun değişikliği hakkında bilgi: "Örnek Davası".',
        priority=2,  # Orta öncelik
        link='https://example.com/dava/1/kanun-degisikligi',
    )

    Notification.objects.create(
        text='Davada uzman görüşü alındı: "Örnek Davası".',
        priority=2,  # Orta öncelik
        link='https://example.com/dava/1/uzman-gorusu',
    )

    Notification.objects.create(
        text='Müvekkil ile görüşme tamamlandı: "Örnek Davası".',
        priority=1,  # Düşük öncelik
        link='https://example.com/dava/1/muvekkil-gorusme',
    )

def calculate_time_until(deadline_date):
    """
    Helper function to calculate time difference from now to deadline_date.
    """
    if not deadline_date:
        return "Tarih belirtilmemiş"

    # Eğer deadline_date bir date ise, datetime'e dönüştür
    if isinstance(deadline_date, date) and not isinstance(deadline_date, datetime):
        deadline_date = datetime.combine(deadline_date, datetime.min.time())

    now = datetime.now()
    delta = deadline_date - now

    if delta.total_seconds() < 0:
        return "Süre dolmuş"

    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes = remainder // 60

    return f"{int(hours)} saat, {int(minutes)} dakika"

@login_required
def notification_list(request):
    """
    View to display the list of unread notifications.
    """
    # Sadece okunmamış (read = False) bildirimleri al
    notifications = Notification.objects.filter(read=False).order_by(
    F('deadline_date').asc(nulls_last=True))

    # Her bildirim için kalan süreyi hesapla ve notification objesine ekle
    for notification in notifications:
        notification.time_until = calculate_time_until(notification.deadline_date)

    context = {
        'notifications': notifications,
    }
    return render(request, 'notifications/notifications.html', context)


@require_POST
def mark_notifications_as_read(request):
    """
    Mark selected notifications as read.
    """
    notification_ids = request.POST.getlist('notification_ids')
    print(notification_ids)
    if notification_ids:
        Notification.objects.filter(id__in=notification_ids).update(read=True)
    return redirect('notification_list')

@login_required
def notification_delete(request, id):
    """
    View to delete a specific notification.
    """
    notification = get_object_or_404(Notification, id=id)
    notification.delete()
    return redirect('notification_list')

@login_required
def show_work_list(request):
    """
    Burada select_related özelliğini kullandım böylece case modelini de sisteme yüklüyor, bunu yapmadan da case bilgisine erişmek mümkün fakat çok uzun sürüyor
    SON YAPILAN İŞ EN ÜSTTE GÖZÜKECEK ŞEKİLDE AYARLADIM TERCİHE BAĞLI DEĞİŞTİRİLEBİLİR
    """
    # Aktif kullanıcının gerçekleştirmiş olduğu tüm işleri al ve ilişkili verileri önceden yükle
    case_progress = CaseProgress.objects.filter(
        created_by=request.user
    ).select_related('case').order_by('-progress_date')  # İlişkili 'case' modelini önceden yükle

    context = {
        'case_progress': case_progress,
    }
    
    return render(request, 'notifications/work_list.html', context)

