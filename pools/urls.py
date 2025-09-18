from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Asosiy sahifalar
    path('', views.home, name='home'),
    path('pools/', views.pool_list, name='pool_list'),
    path('pool/<int:pool_id>/', views.pool_detail, name='pool_detail'),
    path('pool/<int:pool_id>/book/', views.book_pool, name='book_pool'),
    path('booking/success/<uuid:booking_id>/', views.booking_success, name='booking_success'),
    path('booking/receipt/<uuid:booking_id>/', views.download_receipt, name='download_receipt'),
    
    # Foydalanuvchi profili
    path('profile/', views.profile, name='profile'),
    
    # Autentifikatsiya
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Parolni tiklash
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # API endpoints
    path('api/pools/', views.api_pools, name='api_pools'),
    path('api/pool/<int:pool_id>/', views.api_pool_detail, name='api_pool_detail'),
]