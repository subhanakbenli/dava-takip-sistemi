from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .xlsxReader import read_excel_file
import pandas as pd
from Client.models import Case,ProcessTypes,CaseProgress,Notification,DailyFile
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
        file_contents = {}  # DataFrame içeriklerini saklamak için
        number_of_progress,number_of_rows = 0,0 
        for index, excel_file in enumerate(files):
            file_type = file_types[index]
            df = read_excel_file(excel_file)
            df = df.fillna("")
            try:
                if file_type == 'safahat':
                    number_of_progress,number_of_rows, new_df = process_safahat_file(df,request)
                elif file_type == 'tebligat':
                    number_of_progress,number_of_rows, new_df = process_tebligat_file(df,request)
                elif file_type == 'duruşma':
                    number_of_progress,number_of_rows, new_df = process_durusma_file(df,request)
                else:
                    raise ValueError("Geçersiz dosya tipi")
                file_contents[excel_file.name] = new_df.to_dict(orient='records')
                saved_files.append(f'{excel_file.name}:{number_of_progress}:{number_of_rows}')
            except ValueError as e:
                not_saved_files.append(f"{excel_file.name}: {str(e)}")
            except Exception as e:
                not_saved_files.append(f"{excel_file.name}: {str(e)}")

        return JsonResponse({
            "saved_files": saved_files,
            "not_saved_files": not_saved_files,
            "file_contents": file_contents  # DataFrame içerikleri ekleniyor
        })

    return JsonResponse({"error": "Geçersiz istek."}, status=400)


def process_safahat_file(df,request):
    """Safahat dosyasını işler ve ilgili case progress'leri oluşturur."""
    headers = df.columns.tolist()
    rows = df.values.tolist()
    check_is_file_valid(headers, 'safahat')
    number_of_rows = len(rows)
    number_of_progress = 0
    result_list = []
    for row in rows:
        no,islem_yapan_birim, dosya_no, dosya_turu, karar_tarihi, islem_turu, aciklama = extract_safahat_row_data(row, headers)
        
        if islem_turu == -1 and dosya_no == -1 and dosya_turu==-1 and karar_tarihi == -1 and islem_yapan_birim == -1 and aciklama == -1:
            raise ValueError("Dosya formatı hatalı")
        
        current_process = ProcessTypes.objects.filter(process_type=islem_turu).first()
        
        if not current_process:
            current_process = create_missing_process_type(file_type = 'safahat',
                                        process_type=islem_turu,
                                        description ='added automatically',
                                        deadline=5,
                                        priority=1)
        
        date_obj = datetime.strptime(karar_tarihi, "%d.%m.%Y")
        aware_date = timezone.make_aware(date_obj)
        
        progress_text = f"""{islem_yapan_birim} - {dosya_no}  Karar Tarihi : {aware_date.strftime('%Y-%m-%d')}
İşlem Türü:{islem_turu}
Açıklama:{aciklama}"""
        
        related_case = Case.objects.filter(court=islem_yapan_birim, 
                                           case_number=dosya_no,
                                           created_by = request.user).first()
        
        deadline_obj = date_obj + timedelta(days=current_process.deadline)
        aware_deadline = timezone.make_aware(deadline_obj)
        
        if related_case:
            already_has = CaseProgress.objects.filter(case=related_case, 
                                                        progress_date = aware_date,
                                                        description=progress_text,
                                                        created_by = request.user).first()
            # Mevcut dava güncelleniyor
            if already_has:
                result_list.append("Bu işlem zaten eklenmiş")
                continue
            else:
                create_case_progress(case=related_case, progress_date=aware_date,
                                    description=progress_text, 
                                    user = request.user)
                notification_text = f"Dava Güncellendi: {islem_yapan_birim} - {dosya_no}\n{islem_turu}"
                create_notification(text=notification_text,
                                    priority=current_process.priority,
                                    link=f"/case/{related_case.id}",
                                    deadline_date=aware_deadline,
                                    user = request.user)
        
        else:
            # Yeni dava oluşturuluyor
            new_case = create_new_case(islem_yapan_birim, dosya_no,dosya_turu, user = request.user)
            create_case_progress(case=new_case, 
                                 progress_date=aware_date, 
                                 description=progress_text,
                                 user = request.user)
            
            notification_text = f"Safahat ile Otomatik Yeni Dava Eklendi : {islem_yapan_birim} - {dosya_no}\n{islem_turu}"
            create_notification(text=notification_text,
                                priority=3,
                                link=f"/case/{new_case.id}",
                                deadline_date=aware_deadline,
                                user = request.user)
        
        number_of_progress += 1
        result_list.append("İşlem Eklendi")
    df['Yapılan İşlemler'] = result_list
    new_df = df.drop(df[df['Yapılan İşlemler'] == "İşlem Eklendi"].index)
    return number_of_progress, number_of_rows,  new_df

def process_tebligat_file(df,request):
    """Tebligat dosyasını işler ve ilgili case progress'leri oluşturur."""
    df = df.drop(['Boyut'], axis=1, errors='ignore')
    basliklar = df.columns.tolist()
    check_is_file_valid(basliklar, 'tebligat')
    rows = df.values.tolist()
    number_of_rows = len(rows)
    number_of_progress = 0
    result_list = []
    for row in rows:
        gonderen, konu, durum, teslim_tarihi = extract_tebligat_row_data(row)
        
        mahkeme, dosya_no, islem_numarasi = parse_case_details(konu)

        date_obj = datetime.strptime(teslim_tarihi, "%d.%m.%Y %H:%M")
        aware_date = timezone.make_aware(date_obj)
        
        progress_text = f"""{mahkeme} - {dosya_no} - işlem numarası: {islem_numarasi}
Gönderen: {gonderen} Tebligat Durumu : {durum} - Teslim Tarihi : {aware_date.strftime("%Y-%m-%d")}"""
        
        deadline_obj = date_obj + timedelta(days=5)
        aware_deadline = timezone.make_aware(deadline_obj)
        related_case = Case.objects.filter(court=mahkeme, 
                                           case_number=dosya_no,
                                           created_by = request.user).first()
        
        if related_case:
            already_has =CaseProgress.objects.filter(case=related_case,unique_info=islem_numarasi,created_by = request.user,).exists()          
            if already_has:
                result_list.append("Bu işlem zaten eklenmiş")
                continue
            else:
                create_case_progress(case=related_case,
                                    description=progress_text,
                                    unique_info=islem_numarasi,
                                    progress_date=aware_date,
                                    user = request.user)
        
                notification_text = f"Davanıza Tebligat Geldi :{mahkeme}-{dosya_no}"           
                create_notification(text=notification_text, 
                                    priority=1, 
                                    link=f"/case/{related_case.id}", 
                                    deadline_date=aware_deadline,
                                    user= request.user )
                               
        else:        
            new_case = create_new_case(mahkeme, dosya_no, user = request.user)
            create_case_progress(case=new_case,
                                 description=progress_text,
                                 unique_info=islem_numarasi,
                                 progress_date=aware_date,
                                 user = request.user)
            
            notification_text = f"Tebligat ile Yeni Dava Eklendi, müvekkil ekleyiniz : {mahkeme}-{dosya_no}-{islem_numarasi}"
            create_notification(text=notification_text,
                                priority=3,
                                link=f"/case/{new_case.id}" ,
                                deadline_date=aware_deadline,
                                user = request.user)
        
        result_list.append("İşlem Eklendi")
        number_of_progress += 1
    df['Yapılan İşlemler'] = result_list
    new_df = df.drop(df[df['Yapılan İşlemler'] == "İşlem Eklendi"].index)
    return number_of_progress, number_of_rows,  new_df

def process_durusma_file(df,request):
    """Duruşma dosyasını işler ve ilgili case progress'leri oluşturur."""
    df = df.drop('İzinli Hakim', axis=1, errors='ignore')
    rows = df.values.tolist()
    headers = df.columns.tolist()
    check_is_file_valid(headers, 'durusma')
    number_of_rows = len(rows)
    number_of_progress = 0
    result_list = []
    for row in rows:
        mahkeme, dosya_no, dosya_turu, durusma_tarihi, taraf_bilgi, islem, sonuc = extract_durusma_row_data(row)
        progress_text = generate_progress_text_durusma(mahkeme,dosya_no,durusma_tarihi, dosya_turu, islem, sonuc, taraf_bilgi)
        
        date_obj = datetime.strptime(durusma_tarihi, "%d.%m.%Y %H:%M:%S")
        aware_date = timezone.make_aware(date_obj)
        
        related_case = Case.objects.filter(court=mahkeme, case_number=dosya_no,created_by = request.user).first()
        
        deadline_obj = date_obj + timedelta(days=5)
        aware_deadline = timezone.make_aware(deadline_obj)
        
        if related_case:
            already_has = CaseProgress.objects.filter(case=related_case, 
                                                      progress_date=aware_date, 
                                                      description=progress_text,
                                                      created_by = request.user).first()
            if already_has:
                result_list.append("Bu işlem zaten eklenmiş")
                continue
            else:
                create_case_progress(case=related_case,
                                    description=progress_text, 
                                    progress_date=aware_date,
                                    user = request.user)
                notification_text = f"Davanıza Yeni Duruşma Tarihi Eklendi: {mahkeme}-{dosya_no}"
                
                create_notification(text=notification_text, 
                                    priority=1, 
                                    link=f"/case/{related_case.id}", 
                                    deadline_date=aware_deadline,
                                    user = request.user)
            
        else:
            new_case = create_new_case(mahkeme, 
                                       dosya_no=dosya_no,
                                       dosya_turu=dosya_turu,
                                       user = request.user)
            
            create_case_progress(case=new_case,
                                 description=progress_text,
                                 progress_date=aware_date,
                                 user = request.user)   
            notification_text = f"Duruşma ile Dava Eklendi, müvekkil ekleyiniz: {mahkeme}-{dosya_no}"
            
            create_notification(text=notification_text,
                                priority=3,
                                link=f"/case/{new_case.id}",
                                deadline_date=aware_deadline,
                                user = request.user)

        number_of_progress += 1
        result_list.append("İşlem Eklendi")
        
    df['Yapılan İşlemler'] = result_list
    new_df = df.drop(df[df['Yapılan İşlemler'] == "İşlem Eklendi"].index)
    return number_of_progress, number_of_rows,  new_df

def parse_case_details(konu):
    """Konudan mahkeme ve dosya numarasını çıkarır."""
    konu = (konu.split("["))[-1].split("-")
    mahkeme = konu[0].strip()
    dosya_no = konu[-1].replace("]","").strip()
    islem_numarasi = konu[1].strip() if len(konu) > 2 else None
    return mahkeme, dosya_no ,islem_numarasi

def extract_safahat_row_data(row, basliklar):
    """Safahat dosyasındaki bir satırdan gerekli veriyi çıkartır."""
    # No	İşlem Yapan Birim	Dosya No	Tarih	İşlem Türü	Açıklama
    # No	Birim	Dosya No	Dosya Türü	İşlem Türü	İşlem Tarihi	Açıklama

    if basliklar == ['No','Birim','Dosya No','Dosya Türü','İşlem Türü','İşlem Tarihi','Açıklama']:
        return row[0], row[1], row[2],row[3], row[5], row[4], row[6]
    elif basliklar == ['No','İşlem Yapan Birim','Dosya No','Tarih','İşlem Türü','Açıklama']:
        return row[0], row[1],row[2],'İcra Dava Dosyası', row[3], row[4], row[5] if len(row) > 5 else None
    else:
        return -1, -1, -1, -1, -1, -1,-1

def create_missing_process_type(file_type,process_type, description, deadline, priority):
    """İşlem türü bulunamadığında yeni işlem türü oluşturur."""
    new_process_type = ProcessTypes(file_type=file_type, process_type=process_type, deadline=deadline, priority=priority, description=description)
    new_process_type.save()
    return new_process_type

def create_new_case(mahkeme, dosya_no,dosya_turu=None,user=None):
    """Yeni dava kaydeder."""
    print(user)
    new_case = Case(court=mahkeme, case_number=dosya_no, case_type=dosya_turu, created_by=user)
    new_case.save()
    return new_case

def create_case_progress(case, progress_date,unique_info=None, description=None,user=None):
    """Dava ilerleme kaydeder."""
    print(user)
    case_progress = CaseProgress(case=case,
                                 unique_info=unique_info, 
                                 description=description, 
                                 progress_date=progress_date,
                                 created_by=user)
    case_progress.save()

def create_notification(text,priority =3,link=None, deadline_date=None,user=None):
    """Yeni bir bildirim oluşturur."""
    notification = Notification(text=text,
                                priority=priority,
                                link=link,
                                deadline_date=deadline_date,
                                created_by=user)
    notification.save()

def generate_progress_text_durusma(mahkeme,dosya_no,durusma_tarihi, dosya_turu, islem, sonuc, taraf_bilgi):
    """Duruşma için ilerleme metni oluşturur."""
    text=f"""{mahkeme} {dosya_no} Duruşma Tarih:{durusma_tarihi}
Dosya Türü: {dosya_turu} - İşlem: {islem} - Sonuç: {sonuc}
Taraf Bilgisi: {taraf_bilgi}"""
    return text
    
def check_is_file_valid(headers, file_format):
    
    """Dosya formatını kontrol eder."""
    if file_format == 'safahat':
        expected_columns = ['No', 'Birim', 'Dosya No', 'Dosya Türü', 'İşlem Türü', 'İşlem Tarihi', 'Açıklama']
        expected_columns2 = ['No','İşlem Yapan Birim', 'Dosya No', 'Tarih', 'İşlem Türü', 'Açıklama']
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
