#!/usr/bin/env python3
"""
Poolly Telegram Bot
Admin uchun buyurtmalarni boshqarish boti
"""

import asyncio
import logging
import os
import django
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poolly_project.settings')
django.setup()

from django.conf import settings
from pools.models import Booking, Pool

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PoollyBot:
    def __init__(self):
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot boshlash komandasi"""
        user = update.effective_user
        welcome_message = f"""
🏊‍♂️ **Poolly Admin Bot**ga xush kelibsiz, {user.first_name}!

Bu bot orqali siz quyidagilarni amalga oshirishingiz mumkin:

📋 /bookings - Barcha buyurtmalarni ko'rish
🆕 /new_bookings - Yangi buyurtmalarni ko'rish
📊 /stats - Statistikani ko'rish
🏊 /pools - Baseynlar ro'yxati
ℹ️ /help - Yordam

Buyurtmalar haqida avtomatik xabarlar olish uchun botni ishga tushiring.
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yordam komandasi"""
        help_text = """
🤖 **Poolly Admin Bot Komandalar**

📋 `/bookings` - Barcha buyurtmalarni ko'rish
🆕 `/new_bookings` - Yangi buyurtmalarni ko'rish  
📊 `/stats` - Statistikani ko'rish
🏊 `/pools` - Baseynlar ro'yxati
⚙️ `/settings` - Bot sozlamalari

**Buyurtma holatlari:**
• ⏳ Kutilmoqda
• ✅ Tasdiqlangan  
• ❌ Bekor qilingan
• 🏁 Yakunlangan

Har bir buyurtma uchun tugmalar orqali holatni o'zgartirishingiz mumkin.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def show_bookings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Barcha buyurtmalarni ko'rsatish"""
        try:
            bookings = Booking.objects.select_related('pool', 'user').order_by('-created_at')[:10]
            
            if not bookings:
                await update.message.reply_text("📭 Hozircha buyurtmalar yo'q.")
                return
            
            message = "📋 **So'nggi 10 ta buyurtma:**\n\n"
            
            for booking in bookings:
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅', 
                    'cancelled': '❌',
                    'completed': '🏁'
                }.get(booking.status, '❓')
                
                message += f"""
{status_emoji} **#{booking.booking_id}**
👤 {booking.customer_name}
🏊 {booking.pool.name}
📅 {booking.booking_date.strftime('%d.%m.%Y')} ⏰ {booking.start_time.strftime('%H:%M')}
💰 {booking.total_price:,.0f} so'm
📞 {booking.customer_phone}

"""
            
            # Inline tugmalar
            keyboard = [
                [InlineKeyboardButton("🆕 Yangi buyurtmalar", callback_data="new_bookings")],
                [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
                [InlineKeyboardButton("🔄 Yangilash", callback_data="refresh_bookings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Buyurtmalarni ko'rsatishda xatolik: {e}")
            await update.message.reply_text("❌ Buyurtmalarni yuklashda xatolik yuz berdi.")
    
    async def show_new_bookings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yangi buyurtmalarni ko'rsatish"""
        try:
            new_bookings = Booking.objects.filter(status='pending').select_related('pool', 'user').order_by('-created_at')
            
            if not new_bookings:
                await update.message.reply_text("✅ Barcha buyurtmalar ko'rib chiqilgan!")
                return
            
            message = f"🆕 **Yangi buyurtmalar ({new_bookings.count()} ta):**\n\n"
            
            for booking in new_bookings[:5]:  # Faqat 5 tasini ko'rsatish
                message += f"""
⏳ **#{booking.booking_id}**
👤 {booking.customer_name}
🏊 {booking.pool.name}
📅 {booking.booking_date.strftime('%d.%m.%Y')} ⏰ {booking.start_time.strftime('%H:%M')}
👥 {booking.number_of_people} kishi
💰 {booking.total_price:,.0f} so'm
📞 {booking.customer_phone}

"""
            
            # Har bir buyurtma uchun tugmalar
            keyboard = []
            for booking in new_bookings[:3]:  # Faqat 3 tasini tugma qilish
                keyboard.append([
                    InlineKeyboardButton(f"✅ Tasdiqlash #{str(booking.booking_id)[:8]}", 
                                       callback_data=f"confirm_{booking.id}"),
                    InlineKeyboardButton(f"❌ Bekor qilish #{str(booking.booking_id)[:8]}", 
                                       callback_data=f"cancel_{booking.id}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔄 Yangilash", callback_data="new_bookings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Yangi buyurtmalarni ko'rsatishda xatolik: {e}")
            await update.message.reply_text("❌ Yangi buyurtmalarni yuklashda xatolik yuz berdi.")
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Statistikani ko'rsatish"""
        try:
            from django.db.models import Count, Sum
            from datetime import date, timedelta
            
            today = date.today()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Umumiy statistika
            total_bookings = Booking.objects.count()
            total_revenue = Booking.objects.filter(status='completed').aggregate(
                total=Sum('total_price')
            )['total'] or 0
            
            # Bugungi statistika
            today_bookings = Booking.objects.filter(created_at__date=today).count()
            today_revenue = Booking.objects.filter(
                created_at__date=today, 
                status='completed'
            ).aggregate(total=Sum('total_price'))['total'] or 0
            
            # Haftalik statistika
            week_bookings = Booking.objects.filter(created_at__date__gte=week_ago).count()
            week_revenue = Booking.objects.filter(
                created_at__date__gte=week_ago,
                status='completed'
            ).aggregate(total=Sum('total_price'))['total'] or 0
            
            # Status bo'yicha statistika
            status_stats = Booking.objects.values('status').annotate(count=Count('id'))
            
            message = f"""
📊 **Poolly Statistika**

**📈 Umumiy ko'rsatkichlar:**
• Jami buyurtmalar: {total_bookings}
• Jami daromad: {total_revenue:,.0f} so'm

**📅 Bugungi kun:**
• Buyurtmalar: {today_bookings}
• Daromad: {today_revenue:,.0f} so'm

**📆 So'nggi hafta:**
• Buyurtmalar: {week_bookings}
• Daromad: {week_revenue:,.0f} so'm

**📋 Holat bo'yicha:**
"""
            
            status_names = {
                'pending': '⏳ Kutilmoqda',
                'confirmed': '✅ Tasdiqlangan',
                'cancelled': '❌ Bekor qilingan', 
                'completed': '🏁 Yakunlangan'
            }
            
            for stat in status_stats:
                status_name = status_names.get(stat['status'], stat['status'])
                message += f"• {status_name}: {stat['count']}\n"
            
            # Eng mashhur baseynlar
            popular_pools = Booking.objects.values('pool__name').annotate(
                count=Count('id')
            ).order_by('-count')[:3]
            
            if popular_pools:
                message += "\n**🏊 Eng mashhur baseynlar:**\n"
                for i, pool in enumerate(popular_pools, 1):
                    message += f"{i}. {pool['pool__name']}: {pool['count']} buyurtma\n"
            
            keyboard = [[InlineKeyboardButton("🔄 Yangilash", callback_data="stats")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Statistikani ko'rsatishda xatolik: {e}")
            await update.message.reply_text("❌ Statistikani yuklashda xatolik yuz berdi.")
    
    async def show_pools(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Baseynlar ro'yxatini ko'rsatish"""
        try:
            pools = Pool.objects.filter(is_active=True)
            
            if not pools:
                await update.message.reply_text("🏊 Hozircha faol baseynlar yo'q.")
                return
            
            message = f"🏊 **Faol baseynlar ({pools.count()} ta):**\n\n"
            
            for pool in pools:
                amenities = []
                if pool.has_sauna:
                    amenities.append("🧖 Sauna")
                if pool.has_cafe:
                    amenities.append("☕ Kafe")
                if pool.has_sports_area:
                    amenities.append("🏃 Sport")
                if pool.has_parking:
                    amenities.append("🚗 Parking")
                if pool.has_wifi:
                    amenities.append("📶 WiFi")
                
                amenities_text = " • ".join(amenities) if amenities else "Yo'q"
                
                message += f"""
🏊 **{pool.name}**
📍 {pool.address}
💰 {pool.price_per_hour:,.0f} so'm/soat
👥 {pool.capacity} kishi
⏰ {pool.opening_time.strftime('%H:%M')} - {pool.closing_time.strftime('%H:%M')}
🎯 {amenities_text}

"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Baseynlarni ko'rsatishda xatolik: {e}")
            await update.message.reply_text("❌ Baseynlarni yuklashda xatolik yuz berdi.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inline tugma bosilganda"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        try:
            if data == "new_bookings":
                await self.show_new_bookings_callback(query)
            elif data == "stats":
                await self.show_stats_callback(query)
            elif data == "refresh_bookings":
                await self.show_bookings_callback(query)
            elif data.startswith("confirm_"):
                booking_id = int(data.split("_")[1])
                await self.confirm_booking(query, booking_id)
            elif data.startswith("cancel_"):
                booking_id = int(data.split("_")[1])
                await self.cancel_booking(query, booking_id)
                
        except Exception as e:
            logger.error(f"Tugma callback xatoligi: {e}")
            await query.edit_message_text("❌ Xatolik yuz berdi.")
    
    async def confirm_booking(self, query, booking_id):
        """Buyurtmani tasdiqlash"""
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.status = 'confirmed'
            booking.save()
            
            message = f"""
✅ **Buyurtma tasdiqlandi!**

📋 **#{booking.booking_id}**
👤 {booking.customer_name}
🏊 {booking.pool.name}
📅 {booking.booking_date.strftime('%d.%m.%Y')} ⏰ {booking.start_time.strftime('%H:%M')}
💰 {booking.total_price:,.0f} so'm

Mijozga SMS/telefon orqali xabar bering.
            """
            
            await query.edit_message_text(message, parse_mode='Markdown')
            
        except Booking.DoesNotExist:
            await query.edit_message_text("❌ Buyurtma topilmadi.")
        except Exception as e:
            logger.error(f"Buyurtmani tasdiqlashda xatolik: {e}")
            await query.edit_message_text("❌ Buyurtmani tasdiqlashda xatolik yuz berdi.")
    
    async def cancel_booking(self, query, booking_id):
        """Buyurtmani bekor qilish"""
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.status = 'cancelled'
            booking.save()
            
            message = f"""
❌ **Buyurtma bekor qilindi!**

📋 **#{booking.booking_id}**
👤 {booking.customer_name}
🏊 {booking.pool.name}
📅 {booking.booking_date.strftime('%d.%m.%Y')} ⏰ {booking.start_time.strftime('%H:%M')}

Mijozga bekor qilish sababini tushuntiring.
            """
            
            await query.edit_message_text(message, parse_mode='Markdown')
            
        except Booking.DoesNotExist:
            await query.edit_message_text("❌ Buyurtma topilmadi.")
        except Exception as e:
            logger.error(f"Buyurtmani bekor qilishda xatolik: {e}")
            await query.edit_message_text("❌ Buyurtmani bekor qilishda xatolik yuz berdi.")
    
    async def show_bookings_callback(self, query):
        """Buyurtmalarni callback orqali ko'rsatish"""
        try:
            bookings = Booking.objects.select_related('pool', 'user').order_by('-created_at')[:10]
            
            if not bookings:
                await query.edit_message_text("📭 Hozircha buyurtmalar yo'q.")
                return
            
            message = "📋 **So'nggi 10 ta buyurtma:**\n\n"
            
            for booking in bookings:
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'cancelled': '❌', 
                    'completed': '🏁'
                }.get(booking.status, '❓')
                
                message += f"""
{status_emoji} **#{booking.booking_id}**
👤 {booking.customer_name}
🏊 {booking.pool.name}
📅 {booking.booking_date.strftime('%d.%m.%Y')} ⏰ {booking.start_time.strftime('%H:%M')}
💰 {booking.total_price:,.0f} so'm

"""
            
            keyboard = [
                [InlineKeyboardButton("🆕 Yangi buyurtmalar", callback_data="new_bookings")],
                [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
                [InlineKeyboardButton("🔄 Yangilash", callback_data="refresh_bookings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Buyurtmalarni callback orqali ko'rsatishda xatolik: {e}")
            await query.edit_message_text("❌ Buyurtmalarni yuklashda xatolik yuz berdi.")
    
    async def show_new_bookings_callback(self, query):
        """Yangi buyurtmalarni callback orqali ko'rsatish"""
        try:
            new_bookings = Booking.objects.filter(status='pending').select_related('pool', 'user').order_by('-created_at')
            
            if not new_bookings:
                await query.edit_message_text("✅ Barcha buyurtmalar ko'rib chiqilgan!")
                return
            
            message = f"🆕 **Yangi buyurtmalar ({new_bookings.count()} ta):**\n\n"
            
            for booking in new_bookings[:5]:
                message += f"""
⏳ **#{booking.booking_id}**
👤 {booking.customer_name}
🏊 {booking.pool.name}
📅 {booking.booking_date.strftime('%d.%m.%Y')} ⏰ {booking.start_time.strftime('%H:%M')}
👥 {booking.number_of_people} kishi
💰 {booking.total_price:,.0f} so'm
📞 {booking.customer_phone}

"""
            
            keyboard = []
            for booking in new_bookings[:3]:
                keyboard.append([
                    InlineKeyboardButton(f"✅ Tasdiqlash #{str(booking.booking_id)[:8]}", 
                                       callback_data=f"confirm_{booking.id}"),
                    InlineKeyboardButton(f"❌ Bekor qilish #{str(booking.booking_id)[:8]}", 
                                       callback_data=f"cancel_{booking.id}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔄 Yangilash", callback_data="new_bookings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Yangi buyurtmalarni callback orqali ko'rsatishda xatolik: {e}")
            await query.edit_message_text("❌ Yangi buyurtmalarni yuklashda xatolik yuz berdi.")
    
    async def show_stats_callback(self, query):
        """Statistikani callback orqali ko'rsatish"""
        try:
            from django.db.models import Count, Sum
            from datetime import date, timedelta
            
            today = date.today()
            week_ago = today - timedelta(days=7)
            
            total_bookings = Booking.objects.count()
            total_revenue = Booking.objects.filter(status='completed').aggregate(
                total=Sum('total_price')
            )['total'] or 0
            
            today_bookings = Booking.objects.filter(created_at__date=today).count()
            week_bookings = Booking.objects.filter(created_at__date__gte=week_ago).count()
            
            status_stats = Booking.objects.values('status').annotate(count=Count('id'))
            
            message = f"""
📊 **Poolly Statistika**

**📈 Umumiy ko'rsatkichlar:**
• Jami buyurtmalar: {total_bookings}
• Jami daromad: {total_revenue:,.0f} so'm

**📅 Bugun: {today_bookings} buyurtma**
**📆 So'nggi hafta: {week_bookings} buyurtma**

**📋 Holat bo'yicha:**
"""
            
            status_names = {
                'pending': '⏳ Kutilmoqda',
                'confirmed': '✅ Tasdiqlangan',
                'cancelled': '❌ Bekor qilingan',
                'completed': '🏁 Yakunlangan'
            }
            
            for stat in status_stats:
                status_name = status_names.get(stat['status'], stat['status'])
                message += f"• {status_name}: {stat['count']}\n"
            
            keyboard = [[InlineKeyboardButton("🔄 Yangilash", callback_data="stats")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Statistikani callback orqali ko'rsatishda xatolik: {e}")
            await query.edit_message_text("❌ Statistikani yuklashda xatolik yuz berdi.")
    
    def run(self):
        """Botni ishga tushirish"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN sozlanmagan!")
            return
        
        # Application yaratish
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Handlerlarni qo'shish
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("bookings", self.show_bookings))
        self.application.add_handler(CommandHandler("new_bookings", self.show_new_bookings))
        self.application.add_handler(CommandHandler("stats", self.show_stats))
        self.application.add_handler(CommandHandler("pools", self.show_pools))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Botni ishga tushirish
        logger.info("Poolly Telegram Bot ishga tushmoqda...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = PoollyBot()
    bot.run()