from django.shortcuts import render, redirect
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
from django.core.paginator import Paginator
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from django.conf import settings

# Get the absolute paths for credential files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(CURRENT_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CURRENT_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    """Helper function to handle Google Calendar authentication and service creation"""
    creds = None

    # Check if credentials.json exists
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"credentials.json not found at {CREDENTIALS_FILE}. "
            "Download it from Google Cloud Console."
        )

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Handle credential refresh or new authentication
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed credentials
                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())
            except Exception:
                # If refresh fails, remove token and force new authentication
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        # If no valid credentials, start new authentication flow
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8080)
            # Save new credentials
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

@login_required()
def index(request):
    # Get cases and handle pagination
    cases = Case.objects.all().filter(created_by=request.user)
    
    # Get per_page parameter from request, default to 5
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 5

    # Create paginator instance
    paginator = Paginator(cases, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)

    events = []
    calendar_error = None
    
    try:
        # Your existing Google Calendar code here...
        service = get_calendar_service()
        now = datetime.datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        events = events_result.get("items", [])
        formatted_events = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            formatted_events.append({
                'start': start,
                'summary': event.get("summary", "No title"),
                'description': event.get("description", ""),
                'location': event.get("location", ""),
            })
        events = formatted_events

    except FileNotFoundError as e:
        calendar_error = str(e)
    except HttpError as error:
        calendar_error = f"Calendar API error: {error}"
    except Exception as e:
        calendar_error = f"An unexpected error occurred: {e}"

    # Add pagination context
    context = {
        "page_obj": page_obj,
        "events": events,
        "calendar_error": calendar_error,
        "per_page": per_page
    }
    
    return render(request, "anasayfa/index.html", context)

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