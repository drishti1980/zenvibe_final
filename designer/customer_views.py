import re
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .customer_models import CustomerAddress
from .models import Order

class AddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = ["label","full_name","phone","company","address","address_line_2","city","province","postal_code"]
    def clean_postal_code(self):
        value = re.sub(r"[ -]", "", self.cleaned_data["postal_code"].upper())
        if not re.fullmatch(r"[ABCEGHJ-NPRSTVXY][0-9][ABCEGHJ-NPRSTV-Z][0-9][ABCEGHJ-NPRSTV-Z][0-9]", value):
            raise forms.ValidationError("Enter a Canadian postal code, e.g. M5V 3L9.")
        return value[:3]+" "+value[3:]

@login_required
def address_book(request):
    obj = get_object_or_404(CustomerAddress, pk=request.POST.get("address_id"), user=request.user) if request.method=="POST" and request.POST.get("address_id") else (get_object_or_404(CustomerAddress, pk=request.GET["edit"], user=request.user) if request.method=="GET" and request.GET.get("edit") else None)
    form = AddressForm(request.POST or None, instance=obj)
    if request.method=="POST" and form.is_valid():
        address=form.save(commit=False)
        address.user=request.user
        address.is_default=not CustomerAddress.objects.filter(user=request.user).exclude(pk=address.pk).exists() or bool(request.POST.get("make_default")) or address.is_default
        address.save()
        if address.is_default:
            CustomerAddress.objects.filter(user=request.user).exclude(pk=address.pk).update(is_default=False)
        return redirect("designer:address_book")
    return render(request,"designer/address_book.html",{"form":form,"editing":obj,"addresses":CustomerAddress.objects.filter(user=request.user)})

@login_required
@require_POST
def remove_address(request,address_id):
    address=get_object_or_404(CustomerAddress,pk=address_id,user=request.user)
    was_default=address.is_default
    address.delete()
    if was_default:
        next_address=CustomerAddress.objects.filter(user=request.user).first()
        if next_address:
            next_address.is_default=True
            next_address.save(update_fields=["is_default"])
    return redirect("designer:address_book")

@login_required
def account_settings(request):
    if request.method=="POST":
        email=request.POST.get("email","").strip()
        try: forms.EmailField().clean(email)
        except forms.ValidationError:
            messages.error(request,"Enter a valid email address.")
            return redirect("designer:account_settings")
        request.user.first_name=request.POST.get("first_name","").strip()[:150]
        request.user.last_name=request.POST.get("last_name","").strip()[:150]
        request.user.email=email
        request.user.save(update_fields=["first_name","last_name","email"])
        messages.success(request,"Profile updated.")
        return redirect("designer:account_settings")
    return render(request,"designer/account_settings.html")

@login_required
def account_security(request):
    form=PasswordChangeForm(request.user,request.POST or None)
    if request.method=="POST" and form.is_valid():
        update_session_auth_hash(request,form.save())
        messages.success(request,"Password changed.")
        return redirect("designer:account_security")
    return render(request,"designer/account_security.html",{"form":form})

@login_required
def payment_history(request):
    return render(request,"designer/payment_history.html",{"orders":Order.objects.filter(user=request.user).select_related("design","design__product")})
