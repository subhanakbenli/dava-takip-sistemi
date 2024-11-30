from Client.models import Notification, CaseProgress, Note, Case, ActionList # Bildirim modelinin yolu
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import datetime, date, timedelta
from django.db.models import F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import logging


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
    notifications = Notification.objects.filter(read=False, created_by = request.user).order_by(
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

from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
# ... (keep your existing imports)

@login_required
def download_work_list_pdf(request):
    """
    İş listesini PDF formatında indirmek için kullanılır.
    """
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Start with base queryset
    queryset = CaseProgress.objects.filter(
        created_by=request.user
    ).select_related('case')
    
    # Apply date filters if provided
    if start_date:
        queryset = queryset.filter(progress_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(progress_date__lte=end_date)
    
    # Order the results
    case_progress = queryset.order_by('-progress_date')
    
    # Render the PDF template
    html_content = render_to_string('notifications/work_list_pdf_template.html', {
        'case_progress': case_progress,
        'user': request.user,
        'generated_date': datetime.now().strftime("%d-%m-%Y %H:%M"),
        'start_date': start_date,
        'end_date': end_date,
    })
    
    # Generate PDF
    pdf_file = HTML(string=html_content).write_pdf()
    
    # Create response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="is_listesi_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    return response

def show_action_list(request):
    actions = ActionList.objects.filter(
        created_by=request.user
    ).select_related('caseprogress', 'caseprogress__case').order_by('-action_deadline')

    context = {
        'actions': actions,
    }

    return render(request, 'notifications/action_list.html/', context)

@login_required
@require_POST
def add_note(request):
    try:
        # Change this to match the input name in the HTML
        case_id = request.POST.get('case_id')
        # Change this to match the textarea id in the HTML
        note_text = request.POST.get('note-text')

        # Rest of the code remains the same
        if not case_id or not note_text:
            return JsonResponse({
                'status': 'error', 
                'message': 'Eksik bilgi. Lütfen tüm alanları doldurun.'
            })

        # Get the case
        case = Case.objects.get(id=case_id)

        # Create the note
        note = Note.objects.create(
            case=case,
            text=note_text,
            created_by=request.user
        )
        return JsonResponse({
            'status': 'success', 
            'note_id': note.id
        })

    except Case.DoesNotExist:
        return JsonResponse({
            'status': 'error', 
            'message': 'Geçersiz dava.'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        })

@require_POST
@login_required
def delete_action(request, action_id):
    action = ActionList.objects.filter(id=action_id, created_by=request.user).first()
    if action:
        action.delete()
    else:
        messages.error(request, "Aksiyon bulunamadı.")
    return redirect(request.META.get('HTTP_REFERER', 'default_redirect_url'))

@login_required
@require_POST
def add_action(request):
    try:
        # Extract form data
        case_id = request.POST.get('case_id')
        action_description = request.POST.get('description')
        deadline_str = request.POST.get('deadline')

        # Validate input
        if not case_id or not action_description or not deadline_str:
            return JsonResponse({
                'status': 'error', 
                'message': 'Eksik bilgi. Lütfen tüm alanları doldurun.'
            })

        # Convert deadline string to datetime
        try:
            # Assuming the date is in YYYY-MM-DD format from the date input
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({
                'status': 'error', 
                'message': 'Geçersiz tarih formatı.'
            })

        # Find the case progress associated with the case
        try:
            case_progress = CaseProgress.objects.filter(case_id=case_id).first()
            if not case_progress:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Bu dava için henüz bir ilerleme kaydı bulunmamaktadır.'
                })
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': 'Dava ilerlemesi bulunamadı.'
            })

        # Create the action
        action = ActionList.objects.create(
            caseprogress=case_progress,
            action_description=action_description,
            action_deadline=deadline,
            created_by=request.user
        )

        return JsonResponse({
            'status': 'success', 
            'action_id': action.id
        })

    except Exception as e:
        # Log the full error for server-side debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Action creation error: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'status': 'error', 
            'message': 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
        })