from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib import messages
from .models import TwoFactor
from davatakipsistemi.settings import EMAIL_HOST_USER
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
def send_2fa_email(user):
    """Kullanıcıya mevcut 2FA doğrulama kodunu e-posta ile gönderir."""
    if not user.email:
        return "Kullanıcının geçerli bir e-posta adresi bulunamadı. Lütfen e-posta adresini güncelleyin."

    two_factor, created = TwoFactor.objects.get_or_create(user=user)
    if created or not two_factor.code:
        two_factor.set_code()

    html_message = render_to_string('email_templates/2fa_email.html', {'code': two_factor.code})
    plain_message = strip_tags(html_message)

    send_mail(
        'İki Faktörlü Doğrulama Kodu',
        plain_message,
        EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
        html_message=html_message
    )
    return "Doğrulama kodu e-posta ile gönderildi."

def login_request(request):
    """Kullanıcı giriş isteğini yönetir ve 2FA doğrulamasını gerçekleştirir."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        input_code = request.POST.get("verification_code")
        if input_code:  # verify.html üzerinden gelen 2FA kodunu doğrula
            try:
                user = User.objects.get(username=username)
                two_factor = TwoFactor.objects.get(user=user)

                if two_factor.is_code_valid(input_code):
                    login(request, user)
                    two_factor.delete()
                    return redirect("/")
                else:
                    return render(request, "account/verify.html", {
                        "error": "Doğrulama kodu geçersiz veya süresi dolmuş.",
                        "username": username  # verify.html'e kullanıcı adı geçiliyor
                    })
            except (User.DoesNotExist, TwoFactor.DoesNotExist):
                return render(request, "account/login.html", {"error": "Geçersiz kullanıcı veya doğrulama kodu."})

        # Kullanıcı adı ve parolayla ilk doğrulama
        user = authenticate(request, username=username, password=password)
        if user is not None:
            send_2fa_email(user)
            return render(request, "account/verify.html", {
                "error": "Doğrulama kodu gönderildi. Lütfen kontrol edin.",
                "username": username  # verify.html'e kullanıcı adı geçiliyor
            })
        else:
            return render(request, "account/login.html", {"error": "Geçersiz kullanıcı adı veya parola."})
    if request.user.is_authenticated:
        return redirect("/")
    else:
        return render(request, "account/login.html")
    
@login_required
def logout_request(request):
    """Kullanıcıyı çıkış yaptırır."""
    if request.user.is_authenticated:
        logout(request)
        return redirect("/")
    else:
        return redirect("/account/login")