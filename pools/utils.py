import asyncio
from telegram import Bot
from telegram.error import TelegramError
from django.conf import settings
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os
from datetime import datetime

def send_telegram_notification(booking):
    """Telegram orqali admin(lar)ga buyurtma haqida xabar yuborish"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_ADMIN_CHAT_ID:
        return False
    
    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        message = f"""
🏊‍♂️ **YANGI BUYURTMA - POOLLY**

📋 **Buyurtma ID:** `{booking.booking_id}`
👤 **Mijoz:** {booking.customer_name}
📞 **Telefon:** {booking.customer_phone}
🏊 **Baseyn:** {booking.pool.name}
📅 **Sana:** {booking.booking_date.strftime('%d.%m.%Y')}
⏰ **Vaqt:** {booking.start_time.strftime('%H:%M')}
⏱ **Davomiyligi:** {booking.duration_hours} soat
👥 **Odamlar soni:** {booking.number_of_people}
💰 **Umumiy narx:** {booking.total_price:,.0f} so'm

📍 **Manzil:** {booking.customer_address}
🎂 **Yosh:** {booking.customer_age}

{f"📝 **Maxsus so'rovlar:** {booking.special_requests}" if booking.special_requests else ""}

⏰ **Buyurtma vaqti:** {booking.created_at.strftime('%d.%m.%Y %H:%M')}
        """
        
        # Asinxron funksiyani sinxron tarzda ishga tushirish
        asyncio.run(bot.send_message(
            chat_id=settings.TELEGRAM_ADMIN_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        ))
        
        return True
    except Exception as e:
        print(f"Telegram xabar yuborishda xatolik: {e}")
        return False

def generate_booking_pdf(booking):
    """Buyurtma uchun PDF chek yaratish"""
    buffer = BytesIO()
    
    # PDF yaratish
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Maxsus stil yaratish
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center
        textColor=colors.HexColor('#2563eb')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#1f2937')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        textColor=colors.HexColor('#374151')
    )
    
    # PDF mazmuni
    story = []
    
    # Sarlavha
    story.append(Paragraph("🏊‍♂️ POOLLY", title_style))
    story.append(Paragraph("Baseyn Buyurtma Cheki", heading_style))
    story.append(Spacer(1, 20))
    
    # Buyurtma ma'lumotlari
    story.append(Paragraph("📋 Buyurtma Ma'lumotlari", heading_style))
    
    booking_data = [
        ['Buyurtma ID:', str(booking.booking_id)],
        ['Sana:', booking.booking_date.strftime('%d.%m.%Y')],
        ['Vaqt:', booking.start_time.strftime('%H:%M')],
        ['Davomiyligi:', f"{booking.duration_hours} soat"],
        ['Holat:', booking.get_status_display()],
    ]
    
    booking_table = Table(booking_data, colWidths=[2*inch, 3*inch])
    booking_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
    ]))
    
    story.append(booking_table)
    story.append(Spacer(1, 20))
    
    # Baseyn ma'lumotlari
    story.append(Paragraph("🏊 Baseyn Ma'lumotlari", heading_style))
    
    pool_data = [
        ['Nomi:', booking.pool.name],
        ['Manzil:', booking.pool.address],
        ['Sig\'im:', f"{booking.pool.capacity} kishi"],
        ['Soatlik narx:', f"{booking.pool.price_per_hour:,.0f} so'm"],
    ]
    
    pool_table = Table(pool_data, colWidths=[2*inch, 3*inch])
    pool_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
    ]))
    
    story.append(pool_table)
    story.append(Spacer(1, 20))
    
    # Mijoz ma'lumotlari
    story.append(Paragraph("👤 Mijoz Ma'lumotlari", heading_style))
    
    customer_data = [
        ['Ism-familiya:', booking.customer_name],
        ['Telefon:', booking.customer_phone],
        ['Manzil:', booking.customer_address],
        ['Yosh:', f"{booking.customer_age} yosh"],
        ['Odamlar soni:', f"{booking.number_of_people} kishi"],
    ]
    
    customer_table = Table(customer_data, colWidths=[2*inch, 3*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
    ]))
    
    story.append(customer_table)
    story.append(Spacer(1, 20))
    
    # Narx hisoblash
    story.append(Paragraph("💰 Narx Hisoblash", heading_style))
    
    price_data = [
        ['Asosiy narx:', f"{booking.base_price:,.0f} so'm"],
        ['Chegirma:', f"-{booking.discount_amount:,.0f} so'm"],
        ['', ''],
        ['JAMI:', f"{booking.total_price:,.0f} so'm"],
    ]
    
    price_table = Table(price_data, colWidths=[2*inch, 3*inch])
    price_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -2), colors.HexColor('#f3f4f6')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, -2), colors.black),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 10),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -2), 1, colors.HexColor('#e5e7eb')),
        ('GRID', (0, -1), (-1, -1), 2, colors.HexColor('#2563eb'))
    ]))
    
    story.append(price_table)
    story.append(Spacer(1, 30))
    
    # Maxsus so'rovlar
    if booking.special_requests:
        story.append(Paragraph("📝 Maxsus So'rovlar", heading_style))
        story.append(Paragraph(booking.special_requests, normal_style))
        story.append(Spacer(1, 20))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("Poolly platformasidan foydalanganingiz uchun rahmat!", normal_style))
    story.append(Paragraph(f"Chek yaratilgan vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
    
    # PDF yaratish
    doc.build(story)
    buffer.seek(0)
    
    return buffer

def calculate_booking_price(pool, duration_hours, number_of_people, customer_age):
    """Buyurtma narxini hisoblash"""
    base_price = pool.price_per_hour * duration_hours
    
    # Chegirmalarni hisoblash
    discount_percent = 0
    
    # Bolalar uchun chegirma
    if customer_age < 18 and pool.children_discount > 0:
        discount_percent = max(discount_percent, pool.children_discount)
    
    # Guruh uchun chegirma
    if number_of_people >= 5 and pool.group_discount > 0:
        discount_percent = max(discount_percent, pool.group_discount)
    
    discount_amount = (base_price * discount_percent) / 100
    total_price = base_price - discount_amount
    
    return {
        'base_price': base_price,
        'discount_percent': discount_percent,
        'discount_amount': discount_amount,
        'total_price': total_price
    }