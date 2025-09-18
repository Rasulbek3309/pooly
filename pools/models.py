from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Pool(models.Model):
    name = models.CharField(max_length=200, verbose_name="Baseyn nomi")
    description = models.TextField(verbose_name="Tavsif")
    address = models.CharField(max_length=300, verbose_name="Manzil")
    price_per_hour = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Soatlik narx (so'm)"
    )
    capacity = models.PositiveIntegerField(
        verbose_name="Sig'im (nechta odam)",
        validators=[MinValueValidator(1)]
    )
    opening_time = models.TimeField(verbose_name="Ochilish vaqti")
    closing_time = models.TimeField(verbose_name="Yopilish vaqti")
    
    # Qulayliklar
    has_sauna = models.BooleanField(default=False, verbose_name="Sauna bor")
    has_cafe = models.BooleanField(default=False, verbose_name="Kafe bor")
    has_sports_area = models.BooleanField(default=False, verbose_name="Sport maydoni bor")
    has_parking = models.BooleanField(default=False, verbose_name="Parking bor")
    has_wifi = models.BooleanField(default=False, verbose_name="WiFi bor")
    
    # Bonuslar
    children_discount = models.PositiveIntegerField(
        default=0, 
        verbose_name="Bolalar uchun chegirma (%)",
        validators=[MaxValueValidator(100)]
    )
    group_discount = models.PositiveIntegerField(
        default=0,
        verbose_name="Guruh uchun chegirma (%)",
        validators=[MaxValueValidator(100)]
    )
    
    rules = models.TextField(verbose_name="Qoidalar", blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Baseyn"
        verbose_name_plural = "Baseynlar"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class PoolImage(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='pool_images/', verbose_name="Rasm")
    is_main = models.BooleanField(default=False, verbose_name="Asosiy rasm")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Baseyn rasmi"
        verbose_name_plural = "Baseyn rasmlari"
    
    def __str__(self):
        return f"{self.pool.name} - {'Asosiy' if self.is_main else 'Qoshimcha'}"




class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name="Telefon raqam")
    address = models.CharField(max_length=300, verbose_name="Manzil")
    age = models.PositiveIntegerField(verbose_name="Yosh", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Foydalanuvchi profili"
        verbose_name_plural = "Foydalanuvchi profillari"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.phone}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('confirmed', 'Tasdiqlangan'),
        ('cancelled', 'Bekor qilingan'),
        ('completed', 'Yakunlangan'),
    ]
    
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Foydalanuvchi")
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, verbose_name="Baseyn")
    
    # Buyurtma ma'lumotlari
    booking_date = models.DateField(verbose_name="Buyurtma sanasi")
    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    duration_hours = models.PositiveIntegerField(
        verbose_name="Davomiyligi (soat)",
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    number_of_people = models.PositiveIntegerField(
        verbose_name="Odamlar soni",
        validators=[MinValueValidator(1)]
    )
    
    # Mijoz ma'lumotlari
    customer_name = models.CharField(max_length=200, verbose_name="Mijoz ismi")
    customer_phone = models.CharField(max_length=20, verbose_name="Telefon raqam")
    customer_address = models.CharField(max_length=300, verbose_name="Manzil")
    customer_age = models.PositiveIntegerField(verbose_name="Yosh")
    
    # Narx hisoblash
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Asosiy narx")
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Chegirma miqdori"
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Umumiy narx")
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Holat"
    )
    
    special_requests = models.TextField(blank=True, verbose_name="Maxsus so'rovlar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer_name} - {self.pool.name} ({self.booking_date})"
    
    def save(self, *args, **kwargs):
        # Narxni avtomatik hisoblash
        if not self.base_price:
            self.base_price = self.pool.price_per_hour * self.duration_hours
        
        # Chegirmalarni hisoblash
        discount_percent = 0
        if self.customer_age < 18 and self.pool.children_discount > 0:
            discount_percent = max(discount_percent, self.pool.children_discount)
        
        if self.number_of_people >= 5 and self.pool.group_discount > 0:
            discount_percent = max(discount_percent, self.pool.group_discount)
        
        self.discount_amount = (self.base_price * discount_percent) / 100
        self.total_price = self.base_price - self.discount_amount
        
        super().save(*args, **kwargs)