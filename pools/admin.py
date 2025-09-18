from django.contrib import admin
from django.utils.html import format_html
from .models import Pool, PoolImage, UserProfile, Booking

class PoolImageInline(admin.TabularInline):
    model = PoolImage
    extra = 1
    fields = ('image', 'is_main')

@admin.register(Pool)
class PoolAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'address', 'price_per_hour', 'capacity', 
        'opening_time', 'closing_time', 'is_active', 'created_at'
    ]
    list_filter = [
        'is_active', 'has_sauna', 'has_cafe', 'has_sports_area', 
        'has_parking', 'has_wifi', 'created_at'
    ]
    search_fields = ['name', 'address', 'description']
    list_editable = ['is_active', 'price_per_hour']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('name', 'description', 'address', 'price_per_hour', 'capacity')
        }),
        ('Ish vaqti', {
            'fields': ('opening_time', 'closing_time')
        }),
        ('Qulayliklar', {
            'fields': ('has_sauna', 'has_cafe', 'has_sports_area', 'has_parking', 'has_wifi'),
            'classes': ('collapse',)
        }),
        ('Chegirmalar', {
            'fields': ('children_discount', 'group_discount'),
            'classes': ('collapse',)
        }),
        ('Qo\'shimcha', {
            'fields': ('rules', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PoolImageInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('images')

@admin.register(PoolImage)
class PoolImageAdmin(admin.ModelAdmin):
    list_display = ['pool', 'is_main', 'image_preview', 'created_at']
    list_filter = ['is_main', 'created_at']
    search_fields = ['pool__name']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;" />',
                obj.image.url
            )
        return "Rasm yo'q"
    image_preview.short_description = "Rasm"

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'address', 'age', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone']
    list_filter = ['created_at']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_id', 'customer_name', 'pool', 'booking_date', 
        'start_time', 'duration_hours', 'total_price', 'status', 'created_at'
    ]
    list_filter = ['status', 'booking_date', 'created_at', 'pool']
    search_fields = [
        'customer_name', 'customer_phone', 'pool__name', 
        'booking_id', 'user__username'
    ]
    list_editable = ['status']
    date_hierarchy = 'booking_date'
    
    fieldsets = (
        ('Buyurtma ma\'lumotlari', {
            'fields': ('booking_id', 'user', 'pool', 'status')
        }),
        ('Vaqt va davomiyligi', {
            'fields': ('booking_date', 'start_time', 'duration_hours', 'number_of_people')
        }),
        ('Mijoz ma\'lumotlari', {
            'fields': ('customer_name', 'customer_phone', 'customer_address', 'customer_age')
        }),
        ('Narx hisoblash', {
            'fields': ('base_price', 'discount_amount', 'total_price'),
            'classes': ('collapse',)
        }),
        ('Qo\'shimcha', {
            'fields': ('special_requests',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['booking_id', 'base_price', 'discount_amount', 'total_price']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'pool')

# Admin panel sozlamalari
admin.site.site_header = "Poolly Admin Panel"
admin.site.site_title = "Poolly Admin"
admin.site.index_title = "Poolly Boshqaruv Paneli"