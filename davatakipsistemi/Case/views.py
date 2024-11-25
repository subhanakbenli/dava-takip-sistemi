from django.shortcuts import render, redirect, get_object_or_404
from Client.models import Case, Client, CaseProgress, Notification,Note
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import HttpResponseBadRequest, HttpResponseNotFound
@login_required
def add_case(request):
    """
    View function to add a new case. Processes form data from POST requests
    and creates a new Case instance in the database.

    Args:
        request: The HTTP request object.

    Returns:
        Redirects to the new case detail page if successful or re-renders the form if an error occurs.
    """
    if request.method == 'POST':
        # Collect data from the form
        client_id = request.POST.get('client')
        case_number = request.POST.get('case_number')
        case_type = request.POST.get('case_type')
        status = request.POST.get('status')
        # start_date = request.POST.get('start_date')
        # end_date = request.POST.get('end_date')
        # hearing_date = request.POST.get('hearing_date')
        court = request.POST.get('court')
        description = request.POST.get('description')
        case_file = request.FILES.get('case_file')

        # Retrieve the Client instance
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            messages.error(request, "Selected client not found.")
            return redirect('add_case')  # Redirect to form in case of error

        # Create a new Case instance
        case = Case(
            client=client,
            case_number=case_number,
            case_type=case_type,
            status=status,
            # start_date=start_date,
            # end_date=end_date,
            # hearing_date=hearing_date,
            court=court,
            description=description,
            case_file=case_file,
        )

        # Save to the database
        case.save()

        messages.success(request, "Case successfully added.")
        return redirect(f'/case/{case.id}')  # Redirect to case detail page

    # Render form page for GET requests
    clients = Client.objects.all()  # Retrieve all clients
    return render(request, "Case/add_case.html", {'clients': clients})

@login_required
def show_case_detail(request, id):
    """
    View function to display case details based on the case ID.

    Args:
        request: The HTTP request object.
        id: The ID of the case to be displayed.

    Returns:
        Renders the case detail template with case data.
    """
    case = get_object_or_404(Case, id=id, created_by = request.user)
    clients = Client.objects.all().filter(created_by = request.user)
    case_progress_list = CaseProgress.objects.filter(case_id=case.id, created_by = request.user).order_by('-progress_date')
    caseIdLink = f"/case/{case.id}"
    notifications = Notification.objects.filter(link=caseIdLink, read = False, created_by = request.user).order_by('-priority')

    if request.method == 'POST':
        client_id = request.POST.get('client_id')

        if not client_id:
            messages.warning(request, "Client ID is required.")
            return redirect('show_case_detail', id = case.id)
        try:
            client = Client.objects.get(id=client_id)
        except Case.DoesNotExist:
            messages.warning(request, "Selected client not found.")
            return redirect('show_case_detail', id = case.id)

        case.client = client
        case.save()
        return redirect(reverse('show_case_detail', kwargs={'id': case.id}))
    notes = Note.objects.filter(case_id = case.id,created_by = request.user)
    return render(request, "Case/case.html", {"case": case, "clients": clients, "case_progress" : case_progress_list, "notifications" : notifications, "notes" : notes})

@require_POST
def remove_client_from_case(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    case.client = None
    case.save()
    messages.success(request, 'Müvekkil davadan başarıyla kaldırıldı.')
    return redirect('show_case_detail', id = case_id)

@login_required
def show_case_list(request):
    """
    View function to list cases with pagination and sorting functionality.

    Args:
        request: The HTTP request object.

    Returns:
        Renders the case list template with paginated and sorted cases.
    """
    sort_by = request.GET.get("sort_by", "created_at")
    sort_order = request.GET.get("sort_order", "asc")
    per_page = request.GET.get("per_page", "10")

    # Adjust sorting order
    if sort_order == "desc":
        sort_by = f"-{sort_by}"

    # Retrieve cases from the database with sorting
    cases = Case.objects.all().filter(created_by = request.user).order_by(sort_by)

    # Paginate cases
    paginator = Paginator(cases, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "sort_by": request.GET.get("sort_by", "created_at"),
        "sort_order": request.GET.get("sort_order", "asc"),
        "per_page": per_page,
    }

    return render(request, "Case/case_list.html", context)


@login_required
def add_sample_cases(request):
    """
    Utility function to add sample cases to the database for testing purposes.

    Args:
        request: The HTTP request object.

    Returns:
        Renders a confirmation page after adding sample cases.
    """
    sample_cases = [
        {
            "client_id": 1,
            "case_number": "D20231001",
            "case_type": "Criminal",
            "status": "Ongoing",
            "start_date": date(2023, 10, 1),
            "hearing_date": date(2023, 12, 1),
            "court": "İstanbul 2. Ağır Ceza Mahkemesi",
            "description": "Detailed description about the case.",
            "updated_by_id": 1
        },
        {
            "client_id": 3,
            "case_number": "D20231002",
            "case_type": "Civil",
            "status": "Resolved",
            "start_date": date(2023, 8, 15),
            "end_date": date(2023, 10, 20),
            "hearing_date": date(2023, 9, 15),
            "court": "Ankara 1. Asliye Hukuk Mahkemesi",
            "description": "Resolution process of the case is completed.",
            "updated_by_id": 2
        },
        # Additional sample cases
    ]

    for case_data in sample_cases:
        client = Client.objects.get(id=case_data["client_id"])
        updated_by = None  # This can be adjusted if there's a User model for tracking updates

        # Create a Case instance with related foreign keys
        Case.objects.create(
            client=client,
            case_number=case_data["case_number"],
            case_type=case_data["case_type"],
            status=case_data["status"],
            start_date=case_data["start_date"],
            end_date=case_data.get("end_date"),
            hearing_date=case_data.get("hearing_date"),
            court=case_data["court"],
            description=case_data["description"],
            updated_by=updated_by
        )

    return render(request, "Case/sample_cases_added.html")  # Render confirmation page


@require_POST
@login_required
def add_note(request, case_id):
    note_text = request.POST.get('note_text')
    if note_text:
        case = get_object_or_404(Case, id=case_id, created_by=request.user)
        Note.objects.create(case=case, text=note_text, created_by=request.user)
        messages.success(request, "Not başarıyla eklendi.")
    return redirect('show_case_detail', id=case_id)


@require_POST
@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    case_id = note.case.id  # Notun bağlı olduğu davayı almak
    note.delete()
    return redirect('show_case_detail', id=case_id)

@require_POST
@login_required
def update_case_field(request, case_id):
    print("update_case_field")
    case = get_object_or_404(Case, id=case_id)
    field_name = request.POST.get('field_name')
    field_value = request.POST.get('field_value')

    if field_name in ['case_type', 'status', 'description']:
        setattr(case, field_name, field_value)
        case.save()
        # Başarılı bir şekilde güncellendikten sonra kullanıcıyı detay sayfasına yönlendirin
        return redirect('show_case_detail', id=case_id)

    # Eğer hata oluşursa
    return redirect('show_case_detail', id=case_id)

