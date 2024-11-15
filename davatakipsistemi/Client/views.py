from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from .models import Client, Case  # Import the Client model
from decimal import Decimal  # Required for Decimal fields
from datetime import date
from django.core.paginator import Paginator

def add_client(request):
    """
    Adds a new client to the database.

    If the request method is POST, retrieves client information from the form,
    checks for duplicate clients by TC number, and saves the new client if not 
    already registered. Redirects to the client's detail page upon success.
    Renders the client addition form for GET requests.
    """
    if request.method == 'POST':
        # Get data from the form
        name = request.POST.get('first_name')
        surname = request.POST.get('last_name')
        tc_no = request.POST.get('tc_no')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        
        # Other fields (can be taken from the form, assigned fixed values, or omitted)
        agreement_amount = Decimal(request.POST.get('agreement_amount', '0.00'))  # Agreement amount
        amount_received = Decimal(request.POST.get('amount_received', '0.00'))  # Amount received
        remaining_balance = agreement_amount - amount_received  # Remaining balance
        file_expenses = Decimal(request.POST.get('file_expenses', '0.00'))  # File expenses
        
        # Check if the client already exists
        existing_client = Client.objects.filter(tc=tc_no).exists()
        
        if existing_client:
            # Display a warning message or redirect
            messages.warning(request, "This client is already registered.")
            return redirect('add_client')  # Redirect back to the form.
        else:
            # Create a new Client instance
            client = Client(
                tc=tc_no,
                name=name,
                surname=surname,
                address=address,
                phone=phone,
                email=email,
                agreement_amount=agreement_amount,
                amount_received=amount_received,
                remaining_balance=remaining_balance,
                file_expenses=file_expenses,
                files="",  
                notes="",)
        
            # Save the record
            client.save()
            # Redirect to the client's detail page after successful operation
            return redirect(f'/client/{client.id}')
    
    # Render the form page for GET requests
    else:
        return render(request, 'client/add_client.html')

def show_client_detail(request, id):
    """
    Displays the details of a specific client.

    Retrieves the client based on the provided ID and fetches related cases.
    Renders the client detail template with the client's information and cases.
    """
    # Get the Client instance by ID
    client = get_object_or_404(Client, id=id)
    cases_for_client = Case.objects.filter(client_id=id)
    print(cases_for_client)
    context = {
        "client": client,  # Pass the Client instance
        "cases_for_client": cases_for_client,
    }

    # Send the Client instance to the template
    return render(request, "Client/client.html", context)

def show_client_list(request):
    """
    Displays a paginated list of clients.

    Retrieves client data from the database, applies sorting and pagination 
    based on query parameters, and renders the client list template.
    """
    # Get the number of items to show per page
    per_page = request.GET.get('per_page', 10)
    
    # Get sorting parameters (default to sorting by name)
    sort_by = request.GET.get('sort_by', 'name')
    sort_order = request.GET.get('sort_order', 'asc')
    if sort_order == 'desc':
        sort_by = '-' + sort_by

    # Fetch and sort client data from the database
    client_list = Client.objects.all().order_by(sort_by)
    
    # Pagination
    paginator = Paginator(client_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'per_page': per_page,
        'sort_order': sort_order,
        'sort_by': sort_by,
    }
    return render(request, "Client/client_list.html", context)

# views.py
from django.shortcuts import render, get_object_or_404, redirect

def edit_client(request, id):
    client = get_object_or_404(Client, id=id)
    
    if request.method == 'POST':
        # Handle form submission
        client.name = request.POST.get('first_name')
        client.surname = request.POST.get('last_name')
        client.tc = request.POST.get('tc_no')
        client.phone = request.POST.get('phone')
        client.email = request.POST.get('email')
        client.address = request.POST.get('address')
        client.agreement_amount = request.POST.get('agreement_amount')
        client.amount_received = request.POST.get('amount_received')
        client.file_expenses = request.POST.get('file_expenses')
        
        client.save()
        return redirect('client_detail', id=client.id)
    
    return render(request, 'Client/edit_client.html', {'client': client})

from django.http import HttpResponse
from docx import Document
from .models import Client

def download_client_docx(request, client_id):
    client = Client.objects.get(id=client_id)
    document = Document()
    
    document.add_heading(f'Müvekkil: {client.name} {client.surname}', 0)
    document.add_paragraph(f'TC Kimlik No: {client.tc}')
    document.add_paragraph(f'Telefon: {client.phone}')
    document.add_paragraph(f'Email: {client.email}')
    document.add_paragraph(f'Anlaşma Miktarı: {client.agreement_amount}')
    # Add additional fields here...

    # Save to a temporary response file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="{client.name}_{client.surname}.docx"'
    document.save(response)
    
    return response

from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from .models import Client

def download_client_pdf(request, client_id):
    client = Client.objects.get(id=client_id)
    cases_for_client = Case.objects.filter(client_id=client_id)  # If related name for cases is set in the Client model
    
    html_content = render_to_string('Client/client_pdf_template.html', {'client': client, 'cases_for_client': cases_for_client})
    pdf_file = HTML(string=html_content).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{client.name}_{client.surname}.pdf"'
    
    return response


def add_sample_clients(request):
    """
    Adds sample client data to the database.

    Creates multiple client records with predefined sample data.
    """
    # Sample client data
    sample_clients = [
        {
            "tc": "12345678901",
            "name": "Ahmet",
            "surname": "Yılmaz",
            "address": "İstanbul, Türkiye",
            "phone": "05001234567",
            "email": "ahmet@example.com",
            "agreement_amount": Decimal("10000.00"),
            "amount_received": Decimal("5000.00"),
            "remaining_balance": Decimal("5000.00"),
            "file_expenses": Decimal("200.00"),
            "last_sms_date": date(2023, 10, 1),
            "files": "Dosya1, Dosya2",
            "notes": "Önemli not."
        },
        {
            "tc": "98765432109",
            "name": "Mehmet",
            "surname": "Demir",
            "address": "Ankara, Türkiye",
            "phone": "05007654321",
            "email": "mehmet@example.com",
            "agreement_amount": Decimal("15000.00"),
            "amount_received": Decimal("7000.00"),
            "remaining_balance": Decimal("8000.00"),
            "file_expenses": Decimal("300.00"),
            "last_sms_date": date(2023, 9, 15),
            "files": "Dosya3, Dosya4",
            "notes": "Belge eklenecek."
        },
        # Other sample data
        {
            "tc": "11223344556",
            "name": "Ayşe",
            "surname": "Çelik",
            "address": "İzmir, Türkiye",
            "phone": "05553334455",
            "email": "ayse@example.com",
            "agreement_amount": Decimal("20000.00"),
            "amount_received": Decimal("15000.00"),
            "remaining_balance": Decimal("5000.00"),
            "file_expenses": Decimal("500.00"),
            "last_sms_date": date(2023, 10, 20),
            "files": "Dosya5, Dosya6",
            "notes": "SMS gönderilecek."
        },
        {
            "tc": "22334455667",
            "name": "Fatma",
            "surname": "Şahin",
            "address": "Bursa, Türkiye",
            "phone": "05331234567",
            "email": "fatma@example.com",
            "agreement_amount": Decimal("8000.00"),
            "amount_received": Decimal("4000.00"),
            "remaining_balance": Decimal("4000.00"),
            "file_expenses": Decimal("100.00"),
            "last_sms_date": date(2023, 9, 30),
            "files": "Dosya7",
            "notes": "Dava bilgisi güncellenecek."
        },
        {
            "tc": "33445566778",
            "name": "Emre",
            "surname": "Kara",
            "address": "Antalya, Türkiye",
            "phone": "05431234567",
            "email": "emre@example.com",
            "agreement_amount": Decimal("12000.00"),
            "amount_received": Decimal("6000.00"),
            "remaining_balance": Decimal("6000.00"),
            "file_expenses": Decimal("150.00"),
            "last_sms_date": date(2023, 9, 10),
            "files": "Dosya8",
            "notes": "Yeni dosya açılacak."
        },
        # Additional 5 sample client data can be added in the same structure.
    ]

    for client_data in sample_clients:
        Client.objects.create(**client_data)
