from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, date
import json

from .models import Pool, Booking, UserProfile
from .forms import CustomUserCreationForm, BookingForm, UserProfileForm
from .utils import send_telegram_notification, generate_booking_pdf

def home(request):
    """Asosiy sahifa"""
    pools = Pool.objects.filter(is_active=True).prefetch_related('images')[:6]
    
    # Qidiruv
    search_query = request.GET.get('search', '')
    if search_query:
        pools = pools.filter(
            Q(name__icontains=search_query) | 
            Q(address__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'pools': pools,
        'search_query': search_query,
    }
    return render(request, 'pools/home.html', context)

def pool_list(request):
    """Barcha baseynlar ro'yxati"""
    pools = Pool.objects.filter(is_active=True).prefetch_related('images')
    
    # Filtrlash
    search_query = request.GET.get('search', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    has_sauna = request.GET.get('has_sauna')
    has_cafe = request.GET.get('has_cafe')
    
    if search_query:
        pools = pools.filter(
            Q(name__icontains=search_query) | 
            Q(address__icontains=search_query)
        )
    
    if min_price:
        pools = pools.filter(price_per_hour__gte=min_price)
    
    if max_price:
        pools = pools.filter(price_per_hour__lte=max_price)
    
    if has_sauna:
        pools = pools.filter(has_sauna=True)
    
    if has_cafe:
        pools = pools.filter(has_cafe=True)
    
    # Sahifalash
    paginator = Paginator(pools, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'filters': {
            'min_price': min_price,
            'max_price': max_price,
            'has_sauna': has_sauna,
            'has_cafe': has_cafe,
        }
    }
    return render(request, 'pools/pool_list.html', context)

def pool_detail(request, pool_id):
    """Baseyn tafsilotlari"""
    pool = get_object_or_404(Pool, id=pool_id, is_active=True)
    images = pool.images.all()
    
    context = {
        'pool': pool,
        'images': images,
    }
    return render(request, 'pools/pool_detail.html', context)

@login_required
def book_pool(request, pool_id):
    """Baseyn buyurtma berish"""
    pool = get_object_or_404(Pool, id=pool_id, is_active=True)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.pool = pool
            booking.save()
            
            # Telegram orqali xabar yuborish
            send_telegram_notification(booking)
            
            messages.success(request, 'Buyurtma muvaffaqiyatli berildi!')
            return redirect('booking_success', booking_id=booking.booking_id)
    else:
        # Foydalanuvchi profilidan ma'lumotlarni olish
        initial_data = {}
        try:
            profile = request.user.userprofile
            initial_data = {
                'customer_name': request.user.get_full_name(),
                'customer_phone': profile.phone,
                'customer_address': profile.address,
                'customer_age': profile.age,
            }
        except UserProfile.DoesNotExist:
            initial_data = {
                'customer_name': request.user.get_full_name(),
            }
        
        form = BookingForm(initial=initial_data)
    
    context = {
        'form': form,
        'pool': pool,
    }
    return render(request, 'pools/book_pool.html', context)

@login_required
def booking_success(request, booking_id):
    """Buyurtma muvaffaqiyatli yakunlandi"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
    }
    return render(request, 'pools/booking_success.html', context)

@login_required
def download_receipt(request, booking_id):
    """Chek yuklab olish"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    # PDF yaratish
    pdf_buffer = generate_booking_pdf(booking)
    
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="poolly_receipt_{booking.booking_id}.pdf"'
    
    return response

@login_required
def profile(request):
    """Foydalanuvchi profili"""
    try:
        user_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil muvaffaqiyatli yangilandi!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user_profile)
    
    # Foydalanuvchi buyurtmalari
    bookings = Booking.objects.filter(user=request.user).select_related('pool')
    
    context = {
        'form': form,
        'user_profile': user_profile,
        'bookings': bookings,
    }
    return render(request, 'pools/profile.html', context)

def register(request):
    """Ro'yxatdan o'tish"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # UserProfile yaratish
            UserProfile.objects.create(
                user=user,
                phone=form.cleaned_data.get('phone', ''),
                address=form.cleaned_data.get('address', ''),
                age=form.cleaned_data.get('age')
            )
            
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            messages.success(request, 'Ro\'yxatdan o\'tish muvaffaqiyatli yakunlandi!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@csrf_exempt
def api_pools(request):
    """API: Baseynlar ro'yxati"""
    pools = Pool.objects.filter(is_active=True).prefetch_related('images')
    
    pools_data = []
    for pool in pools:
        main_image = pool.images.filter(is_main=True).first()
        pools_data.append({
            'id': pool.id,
            'name': pool.name,
            'description': pool.description,
            'address': pool.address,
            'price_per_hour': str(pool.price_per_hour),
            'capacity': pool.capacity,
            'opening_time': pool.opening_time.strftime('%H:%M'),
            'closing_time': pool.closing_time.strftime('%H:%M'),
            'main_image': main_image.image.url if main_image else None,
            'amenities': {
                'sauna': pool.has_sauna,
                'cafe': pool.has_cafe,
                'sports_area': pool.has_sports_area,
                'parking': pool.has_parking,
                'wifi': pool.has_wifi,
            },
            'discounts': {
                'children': pool.children_discount,
                'group': pool.group_discount,
            }
        })
    
    return JsonResponse({'pools': pools_data})

@csrf_exempt
def api_pool_detail(request, pool_id):
    """API: Baseyn tafsilotlari"""
    pool = get_object_or_404(Pool, id=pool_id, is_active=True)
    images = pool.images.all()
    
    pool_data = {
        'id': pool.id,
        'name': pool.name,
        'description': pool.description,
        'address': pool.address,
        'price_per_hour': str(pool.price_per_hour),
        'capacity': pool.capacity,
        'opening_time': pool.opening_time.strftime('%H:%M'),
        'closing_time': pool.closing_time.strftime('%H:%M'),
        'rules': pool.rules,
        'images': [{'url': img.image.url, 'is_main': img.is_main} for img in images],
        'amenities': {
            'sauna': pool.has_sauna,
            'cafe': pool.has_cafe,
            'sports_area': pool.has_sports_area,
            'parking': pool.has_parking,
            'wifi': pool.has_wifi,
        },
        'discounts': {
            'children': pool.children_discount,
            'group': pool.group_discount,
        }
    }
    
    return JsonResponse(pool_data)