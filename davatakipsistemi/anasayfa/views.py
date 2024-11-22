from django.shortcuts import render
from django.http.response import HttpResponse
from Client.models import Case
from Client.models import Client
from django.contrib.auth import login
from django.contrib.auth.models import User
import datetime
import os.path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required

# Create your views here.

from django.core.paginator import Paginator

@login_required()
def index(request):
    # Bir kullanıcı objesi oluştur veya mevcut kullanıcıyı al
    # test_user, created = User.objects.get_or_create(username="your_test_username")

    # Giriş yapmış gibi ayarla
    # login(request, test_user)
    cases = Case.objects.all().order_by('case_number')  # Order by latest cases
    paginator = Paginator(cases, 3)  # Show 10 cases per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Google Calendar API ayarları
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds = None
    events = []
    
    # token_path = os.path.join(os.path.dirname(__file__), "token.json")
    # if os.path.exists(token_path):
    #     creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # if creds:
    #     try:
    #         service = build("calendar", "v3", credentials=creds)
    #         now = datetime.datetime.utcnow().isoformat() + "Z"  # UTC formatında şu anki zaman
    #         events_result = service.events().list(
    #             calendarId="primary",
    #             timeMin=now,
    #             maxResults=10,
    #             singleEvents=True,
    #             orderBy="startTime",
    #         ).execute()
    #         events = events_result.get("items", [])
            
    #     except HttpError as error:
    #         print(f"Google Calendar API Hatası: {error}")

    # Hem case verilerini hem de takvim etkinliklerini şablona gönder
    return render(request, "anasayfa/index.html", {"page_obj": page_obj, "events": events})


# def index(request):

#     cases = Case.objects.all()  # Veritabanından tüm dava kayıtlarını çekiyoruz
#     for case in cases:
#         print(case.case_number)
#     return render(request, 'anasayfa/index.html', {'cases': cases})

@login_required
def muvekkildetay(request, id):
    return render(request, "anasayfa/muvekkildetay.html", {
        "id" : id
    })

@login_required

def search_cases_clients(request):
    query = request.GET.get('q', '')
    results = []
    
    if len(query) >= 2:  # Only search if query is at least 2 characters
        # Search in Cases
        cases = Case.objects.filter(
            Q(case_number__icontains=query) |
            Q(case_type__icontains=query) |
            Q(status__icontains=query) |
            Q(court__icontains=query) |
            Q(description__icontains=query) |
            Q(client__name__icontains=query) |
            Q(client__surname__icontains=query)
        ).select_related('client')[:10]  # Limit to 10 results

        # Search in Clients
        clients = Client.objects.filter(
            Q(tc__icontains=query) |
            Q(name__icontains=query) |
            Q(surname__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )[:10]  # Limit to 10 results

        # Format case results
        for case in cases:
            results.append({
                'type': 'case',
                'id': case.id,
                'title': f"Dava: {case.case_number}",
                'subtitle': f"{case.client.name} {case.client.surname}",
                'details': f"{case.case_type} - {case.status}",
                'url': f"/case/{case.id}"  # Add your case detail URL pattern
            })

        # Format client results
        for client in clients:
            results.append({
                'type': 'client',
                'id': client.id,
                'title': f"Müvekkil: {client.name} {client.surname}",
                'subtitle': f"TC: {client.tc}",
                'details': f"Tel: {client.phone}",
                'url': f"/client/{client.id}"  # Add your client detail URL pattern
            })

    return JsonResponse({'results': results})