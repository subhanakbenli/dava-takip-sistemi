from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from Client.models import DailyFile
from django.views.decorators.csrf import csrf_exempt
from .xlsxReader import read_excel_file
import pandas as pd
from Client.models import Case,ProcessTypes,CaseProgress,Notification
from datetime import datetime, timedelta
from django.contrib import messages
from django.utils import timezone



def add_process_type():
    df =read_excel_file("C:/Users/suakb/supi/bionluk/dava-takip-sistemi/excelIcerikleri/işlem türleri avukat1.xlsx")
    liste = df.values.tolist()
    for row in liste:
        process_type = row[1]
        deadline = row[2]
        priority = row[3]
        new_process_type = ProcessTypes(file_type = 'safahat',process_type=process_type, deadline=deadline, priority=priority)
        new_process_type.save()

@login_required
def upload_page(request):
    """Yükleme sayfasını render eder."""
    return render(request, 'fileIO/upload_daily.html')  # upload_daily.html şablonunu yükler

@login_required
@csrf_exempt
def upload_file(request):
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        file_types = request.POST.getlist('file_types')
        saved_files = []
        not_saved_files = []

        for index, excel_file in enumerate(files):
            file_type = file_types[index]
            df = read_excel_file(excel_file)

            try:
                if file_type == 'safahat':
                    process_safahat_file(df)
                elif file_type == 'tebligat':
                    process_tebligat_file(df)
                elif file_type == 'duruşma':
                    process_durusma_file(df)
                else:
                    raise ValueError("Geçersiz dosya tipi")

                saved_files.append(excel_file.name)
            except ValueError as e:
                not_saved_files.append(f"{excel_file.name}: {str(e)}")
            except Exception as e:
                not_saved_files.append(f"{excel_file.name}: {str(e)}")

        return JsonResponse({
            "saved_files": saved_files,
            "not_saved_files": not_saved_files
        })

    return JsonResponse({"error": "Geçersiz istek."}, status=400)

def process_safahat_file(df):
    """Safahat dosyasını işler ve ilgili case progress'leri oluşturur."""
    df = df.drop('No', axis=1)
    headers = df.columns.tolist()
    rows = df.values.tolist()
    check_is_file_valid(headers, 'safahat')
    
    for row in rows:
        islem_yapan_birim, dosya_no, karar_tarihi, islem_turu, aciklama = extract_safahat_row_data(row, headers)
        
        if islem_turu == -1 and dosya_no == -1 and karar_tarihi == -1 and islem_yapan_birim == -1 and aciklama == -1:
            raise ValueError("Dosya formatı hatalı")
        
        current_process = ProcessTypes.objects.filter(process_type=islem_turu).first()
        
        if not current_process:
            log_missing_process_type(islem_turu)
            continue
        
        date_obj = datetime.strptime(karar_tarihi, "%d.%m.%Y")
        aware_date = timezone.make_aware(date_obj)
        
        progress_text = f"Karar Tarihi : {aware_date.strftime('%Y-%m-%d')}\nİşlem Türü:{islem_turu}\nAçıklama:{aciklama}"
        
        related_case = Case.objects.filter(court=islem_yapan_birim, case_number=dosya_no).first()
        
        deadline_obj = date_obj + timedelta(days=current_process.deadline)
        aware_deadline = timezone.make_aware(deadline_obj)
        
        if related_case:
            # Mevcut dava güncelleniyor
            create_case_progress(case=related_case, progress_date=aware_date, description=progress_text)
            
            notification_text = f"Dava Güncellendi: {islem_yapan_birim} - {dosya_no}\n{islem_turu}"
            create_notification(text=notification_text,
                                priority=current_process.priority,
                                link=f"/case/{related_case.id}",
                                deadline_date=aware_deadline)
        
        else:
            # Yeni dava oluşturuluyor
            new_case = create_new_case(islem_yapan_birim, dosya_no)
            create_case_progress(case=new_case, progress_date=aware_date, description=progress_text)
            
            notification_text = f"Safahat ile Otomatik Yeni Dava Eklendi : {islem_yapan_birim} - {dosya_no}\n{islem_turu}"
            create_notification(text=notification_text,
                                priority=3,
                                link=f"/case/{new_case.id}",
                                deadline_date=aware_deadline)

def process_tebligat_file(df):
    """Tebligat dosyasını işler ve ilgili case progress'leri oluşturur."""
    df = df.drop(['Boyut'], axis=1, errors='ignore')
    basliklar = df.columns.tolist()
    check_is_file_valid(basliklar, 'tebligat')
    rows = df.values.tolist()
    for row in rows:
        gonderen, konu, durum, teslim_tarihi = extract_tebligat_row_data(row)
        
        mahkeme, dosya_no = parse_case_details(konu)

        date_obj = datetime.strptime(teslim_tarihi, "%d.%m.%Y %H:%M")
        aware_date = timezone.make_aware(date_obj)
        
        progress_text = f"""Gönderen: {gonderen} Tebligat Durumu : {durum} - Teslim Tarihi : {aware_date.strftime("%Y-%m-%d")}"""
        related_case = Case.objects.filter(court=mahkeme, case_number=dosya_no).first()
        
        deadline_obj = date_obj + timedelta(days=5)
        aware_deadline = timezone.make_aware(deadline_obj)
        
        if related_case:
            create_case_progress(case=related_case,
                                 description=progress_text, 
                                 progress_date=aware_date)
    
            notification_text = f"Davanıza Tebligat Geldi :{mahkeme}-{dosya_no}"           
            create_notification(text=notification_text, 
                                priority=1, 
                                link=f"/case/{related_case.id}", 
                                deadline_date=aware_deadline)
        else:        
            new_case = create_new_case(mahkeme, dosya_no)
            create_case_progress(case=new_case,
                                 description=progress_text,
                                 progress_date=aware_date)
            
            notification_text = f"Tebligat ile Yeni Dava Eklendi, müvekkil ekleyiniz : {mahkeme}-{dosya_no}"
            create_notification(text=notification_text,
                                priority=3,
                                link=f"/case/{new_case.id}" ,
                                deadline_date=aware_deadline)


def process_durusma_file(df):
    """Duruşma dosyasını işler ve ilgili case progress'leri oluşturur."""
    df = df.drop('İzinli Hakim', axis=1, errors='ignore')
    rows = df.values.tolist()
    headers = df.columns.tolist()
    check_is_file_valid(headers, 'durusma')
    
    for row in rows:
        mahkeme, dosya_no, dosya_turu, durusma_tarihi, taraf_bilgi, islem, sonuc = extract_durusma_row_data(row)
        progress_text = generate_progress_text_durusma(durusma_tarihi, dosya_turu, islem, sonuc, taraf_bilgi)
        
        date_obj = datetime.strptime(durusma_tarihi, "%d.%m.%Y %H:%M:%S")
        aware_date = timezone.make_aware(date_obj)
        
        related_case = Case.objects.filter(court=mahkeme, case_number=dosya_no).first()
        
        deadline_obj = date_obj + timedelta(days=5)
        aware_deadline = timezone.make_aware(deadline_obj)
        
        if related_case:
            notification_text = f"Davanıza Yeni Duruşma Tarihi Eklendi: {mahkeme}-{dosya_no}"

            create_case_progress(case=related_case,
                                 description=progress_text, 
                                 progress_date=aware_date)
            create_notification(text=notification_text, 
                                priority=1, 
                                link=f"/case/{related_case.id}", 
                                deadline_date=aware_deadline)
        
        else:
            notification_text = f"Duruşma ile Dava Eklendi, müvekkil ekleyiniz: {mahkeme}-{dosya_no}"
            new_case = create_new_case(mahkeme, dosya_no)
            
            create_case_progress(case=new_case,
                                 description=progress_text,
                                 progress_date=aware_date)
            create_notification(text=notification_text,
                                priority=3,
                                link=f"/case/{new_case.id}",
                                deadline_date=aware_deadline)


def update_case_progress(related_case, islem_turu, aciklama, karar_tarihi):
    """Mevcut dava için ilerleme kaydeder."""
    

def parse_case_details(konu):
    """Konudan mahkeme ve dosya numarasını çıkarır."""
    konu = (konu.split("["))[-1].split("-")
    mahkeme = konu[0].strip()
    dosya_no = konu[-1].replace("]","").strip()
            
    return mahkeme, dosya_no

def extract_safahat_row_data(row, basliklar):
    """Safahat dosyasındaki bir satırdan gerekli veriyi çıkartır."""
    # No	İşlem Yapan Birim	Dosya No	Tarih	İşlem Türü	Açıklama
    # No	Birim	Dosya No	Dosya Türü	İşlem Türü	İşlem Tarihi	Açıklama

    if basliklar == ['Birim','Dosya No','Dosya Türü','İşlem Türü','İşlem Tarihi','Açıklama']:
        return row[0], row[1], row[4], row[3], row[5]
    elif basliklar == ['İşlem Yapan Birim','Dosya No','Tarih','İşlem Türü','Açıklama']:
        return row[0], row[1], row[2], row[3], row[4] if len(row) > 4 else None
    else:
        return -1, -1, -1, -1, -1

def log_missing_process_type(islem_turu):
    """İşlem türü bulunamadığında log kaydeder."""
    with open("bulunamayan.txt", "a+", encoding="utf-8") as f:
        f.write(islem_turu + "\n")
    print("İşlem türü bulunamadı")

def create_new_case(mahkeme, dosya_no):
    """Yeni dava kaydeder."""
    new_case = Case(court=mahkeme, case_number=dosya_no)
    new_case.save()
    return new_case


def create_case_progress(case, progress_date, description=None):
    """Dava ilerleme kaydeder."""
    case_progress = CaseProgress(case=case, description=description, progress_date=progress_date)
    case_progress.save()


def create_notification(text,priority =3,link=None, deadline_date=None):
    """Yeni bir bildirim oluşturur."""
    notification = Notification(text=text,
                                priority=priority,
                                link=link,
                                deadline_date=deadline_date)
    notification.save()

def generate_progress_text_durusma(durusma_tarihi, dosya_turu, islem, sonuc, taraf_bilgi):
    """Duruşma için ilerleme metni oluşturur."""
    return f"Dava Duruşma Güncellemesi Tarih:{durusma_tarihi}\nDosya Türü: {dosya_turu} - İşlem: {islem} - Sonuç: {sonuc}\nTaraf Bilgisi: {taraf_bilgi}"

def check_is_file_valid(headers, file_format):
    
    """Dosya formatını kontrol eder."""
    if file_format == 'safahat':
        expected_columns = ['İşlem Yapan Birim', 'Dosya No', 'Tarih', 'İşlem Türü', 'Açıklama']
        expected_columns2 = ['Birim', 'Dosya No', 'Dosya Türü', 'İşlem Türü', 'İşlem Tarihi', 'Açıklama']
        if  headers == expected_columns or headers == expected_columns2:
            return
        else:
            raise ValueError("Dosya formatı hatalı")
    elif file_format == 'tebligat':
        # Gönderen	Konu	Durumu	Teslim Tarihi	Silineceği Tarih

        expected_columns = ['Gönderen', 'Konu', 'Durumu', 'Teslim Tarihi', 'Silineceği Tarih']
        
    elif file_format == 'durusma':
        # Birim	Dosya No	Dosya Turu	Duruşma Tarihi	Taraf Bilgisi	İşlem	Sonuç

        expected_columns = ['Birim', 'Dosya No', 'Dosya Turu', 'Duruşma Tarihi', 'Taraf Bilgisi', 'İşlem', 'Sonuç']
    else:
        raise ValueError("Geçersiz dosya formatı")
    if headers != expected_columns:
        raise ValueError("Dosya formatı hatalı")
    

def extract_tebligat_row_data(row):
    """Tebligat dosyasındaki bir satırdan gerekli veriyi çıkartır."""
    gonderen = row[0]
    konu = row[1]
    durum = row[2]
    teslim_tarihi = row[3]
    return gonderen, konu, durum, teslim_tarihi

def extract_durusma_row_data(row):
    """Duruşma dosyasındaki bir satırdan gerekli veriyi çıkartır."""
    return row[0], row[1], row[2], row[3], row[4], row[5], row[6]

def format_datetime(date_str):
    """Tarihi ve saati doğru formatta dönüştürür."""
    date_obj = datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S")
    return date_obj.strftime("%Y-%m-%d %H:%M:%S")
