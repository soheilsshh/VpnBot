import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, CallbackContext
)

from marzpy import Marzban
from database import *
from config import *
import json
import os
import traceback
import psutil
from aiohttp import ClientError, ClientSession
import pytz
from typing import Dict, Any, Optional, List, Union

from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class LogManager:
    def __init__(self, db):
        self.db = db

    async def log(self, level: str, module: str, message: str, details: dict = None):
        try:
            self.db.log_system(level, module, message, details)
        except Exception as e:
            logger.error(f"Failed to create log entry: {e}")

class ErrorHandler:
    def __init__(self, bot):
        self.bot = bot

    async def handle_error(self, update: Update, context: CallbackContext):
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                if user_id == ADMIN_ID:
                    await context.bot.send_message(
                        ADMIN_ID,
                        f"❌ خطای سیستم:\n{str(context.error)}"
                    )
                else:
                    await context.bot.send_message(
                        user_id,
                        "❌ متأسفانه خطایی رخ داده است. لطفاً مجدداً تلاش کنید."
                    )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

class VPNBot:
    def __init__(self):
        self.db = Database(DATABASE_URL)
        self.marzban = Marzban(
            MARZBAN_CONFIG["username"],
            MARZBAN_CONFIG["password"],
            MARZBAN_CONFIG["url"]
        )
        self.log_manager = LogManager(self.db)
        self.error_handler = ErrorHandler(self)
        self.system_monitor = SystemMonitor(self)
        self.cleanup_manager = CleanupManager(self)

    async def initialize(self):
        """Initialize bot with optimizations"""
        await self.marzban.get_token()
        self._create_default_services()

        # Start background tasks
        asyncio.create_task(self.system_monitor.start_monitoring())
        asyncio.create_task(self.cleanup_manager.start_cleanup())
        asyncio.create_task(self.setup_notifications())

    async def _cleanup_cache(self):
        """Periodic cache cleanup"""
        while True:
            try:
                await self.cache_manager.clear_expired()
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(300)

    def _create_default_services(self):
        """Create default services in database"""
        for template in SERVICE_TEMPLATES.values():
            self.db.create_service(
                name=template["name"],
                price=template["price"],
                duration=template["duration"],
                data_limit=template["data_limit"],
                inbound_id=template["inbound_id"]
            )

    async def start(self, update: Update, context: CallbackContext):
        """Start command handler"""
        try:
            user_id = update.effective_user.id

            # Create or get user
            user = self.db.get_user(user_id)
            if not user:
                self.db.create_user(
                    telegram_id=user_id,
                    username=update.effective_user.username,
                    is_admin=(user_id == ADMIN_ID)
                )

            # Create keyboard
            keyboard = [
                [InlineKeyboardButton("🛒 خرید سرویس", callback_data='buy_service')],
                [InlineKeyboardButton("👤 حساب کاربری", callback_data='user_account')],
                [InlineKeyboardButton("📊 اطلاعات سرویس", callback_data='service_info')]
            ]

            if user_id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data='admin_panel')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send welcome message
            await update.message.reply_text(
                text=MESSAGES["welcome"],
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ خطایی رخ داده است. لطفاً مجدداً تلاش کنید.")

    async def handle_callback(self, update: Update, context: CallbackContext):
        """Handle callback queries"""
        try:
            query = update.callback_query
            await query.answer()

            # Default handlers first
            handlers = {
                'buy_service': self.show_services,
                'user_account': self.show_user_account,
                'admin_panel': self.show_admin_panel,
                'back_to_main': self.back_to_main,
                'charge_wallet': self.handle_wallet_charge,
                'service_info': self.show_service_info,
                'confirm_purchase' : self.handle_purchase_confirmation,
                'extend_service' : self.handle_extend_service,
                'admin_sales_report': self.show_sales_report,
                'admin_users': self.manage_users,
                'admin_discount_codes': self.manage_discount_codes,
                'admin_broadcast': self.broadcast_message,
                'admin_services': self.manage_services,
                'detailed_report': self.detailed_report,
                'report_daily': self.show_report,
                'report_weekly': self.show_report,
                'report_monthly': self.show_report,
                'report_custom': self.show_report,
                'active_users': self.show_active_users,
                'add_discount': self.add_discount_code,
                'list_discount_codes': self.list_discount_codes,
                'discount_type_percent' : self.handle_discount_type,
                'discount_type_fixed' : self.handle_discount_type,
                'broadcast_inactive' : self.handle_broadcast_message,
                'broadcast_active':self.handle_broadcast_message,
                'broadcast_all' : self.handle_broadcast_message,
                'add_service' : self.add_service,
                'edit_services' : self.edit_services,
                'inbound_settings' : self.manage_inbounds,
                'renewal_settings' : self.renewal_settings
            }

            handler = handlers.get(query.data)
            if handler:
                await handler(update, context)
                return

            # Then handle pattern-based callbacks
            if query.data.startswith('service_'):
                await self.handle_service_purchase(update, context)
                return

            if query.data.startswith('confirm_purchase_'):
                await self.handle_purchase_confirmation(update, context)
                return

            if query.data.startswith('charge_') and query.data != 'charge_wallet':####
                await self.process_payment(update, context)
                return

            if query.data.startswith('confirm_payment_'):
                await self.handle_payment_confirmation(update, context)
                return
            if query.data.startswith('edit_service_details_'):
                await self.edit_service_details(update , context)
                
            if query.data.startswith('edit_service_name_'):
                await self.edit_service_name(update,context)
                
            if query.data.startswith('edit_service_duration_'):
                await self.edit_service_duration(update,context)   
                
            if query.data.startswith('edit_service_price_'):
                await self.edit_service_price(update,context)
            
            if query.data.startswith('edit_service_data_limit_'):
                await self.edit_service_data_limit(update,context)
            
            if query.data.startswith('toggle_service_'):
                await self.toggle_service(update , context)
            
            if query.data.startswith('delete_service_'):
                await self.delete_service(update , context)
            
            
                
            logger.warning(f"Unknown callback data: {query.data}")

        except Exception as e:
            logger.error(f"Error in handle_callback: {e}")
            await query.edit_message_text(
                "❌ خطا در پردازش درخواست. لطفاً مجدداً تلاش کنید."
            )

    async def show_services(self, update: Update, context: CallbackContext):
        """Show available services"""
        try:
            services = self.db.get_active_services()

            keyboard = []
            for service in services:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{service.name} - {service.price,} تومان",  # name - price
                        callback_data=f"service_{service.id}"     # service id
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                "📦 لطفاً سرویس مورد نظر خود را انتخاب کنید:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in show_services: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در نمایش سرویس‌ها. لطفاً مجدداً تلاش کنید."
            )

    async def create_marzban_user(self, username: str, service: Dict[str, Any]):
        """Create user in Marzban panel"""

        #TODO: handle this later

        # expire_date = datetime.utcnow() + timedelta(days=service['duration'])
        # user_data = {
        #     "username": username,
        #     "expire": int(expire_date.timestamp()),
        #     "data_limit": service['data_limit'] * 1024 * 1024 * 1024,  # Convert GB to bytes
        #     "inbound_id": service['inbound_id']
        # }
        # return await self.marzban.create_user(user_data)

        return {'success':True}

    async def show_user_account(self, update: Update, context: CallbackContext):
        """Show user account information"""
        try:
            user_id = update.effective_user.id
            user = self.db.get_user(user_id)
            active_services = self.db.get_user_active_services(user.id)

            text = f"""
👤 اطلاعات حساب کاربری:
💰 موجودی کیف پول: {user.wallet_balance} تومان

🌟 سرویس‌های فعال:
"""
            for service in active_services:
                expire_date = service[4]
                remaining_days = (expire_date - datetime.utcnow()).days
                remaining_gb = (service[5] - service[6]) / 1024  # Convert to GB

                text += f"""
• {service[8]}  # service name
📅 {remaining_days} روز مانده
📊 {remaining_gb:.1f} GB حجم باقیمانده
"""

            keyboard = [
                [InlineKeyboardButton("💰 شارژ کیف پول", callback_data='charge_wallet')],
                [InlineKeyboardButton("🔄 تمدید سرویس", callback_data='extend_service')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error in show_user_account: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در نمایش اطلاعات حساب. لطفاً مجدداً تلاش کنید."
            )

    async def handle_service_purchase(self, update: Update, context: CallbackContext):
        """Handle service purchase"""
        try:
            query = update.callback_query
            service_id = int(query.data.split('_')[1])

            # Get user and service
            user = self.db.get_user(update.effective_user.id)
            service = self.db.get_service(service_id)

            if not service:
                await query.edit_message_text("❌ سرویس مورد نظر یافت نشد.")
                return

            if user.wallet_balance < service.price:  # wallet_balance < price
                await query.edit_message_text(
                    MESSAGES["insufficient_balance"],
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💰 شارژ کیف پول", callback_data='charge_wallet')
                    ]])
                )
                return

            # Show purchase confirmation
            keyboard = [
                [InlineKeyboardButton("✅ تایید و پرداخت", callback_data=f'confirm_purchase_{service_id}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='buy_service')]
            ]

            text = f"""
🛍 خرید سرویس:
نام: {service.name}
قیمت: {service.price:,} تومان
مدت: {service.duration} روز
حجم: {service.data_limit} GB

💰 موجودی کیف پول: {user.wallet_balance:,} تومان
"""

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error in handle_service_purchase: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در پردازش درخواست. لطفاً مجدداً تلاش کنید."
            )

    async def handle_extend_service(self, update: Update, context: CallbackContext):
        """Handle extend service"""
        try:
            query = update.callback_query

            user = self.db.get_user(update.effective_user.id)
            active_service = self.db.get_user_active_services(user.id)
            service = self.db.get_service(active_service[0][2])

            if not service:
                await query.edit_message_text("❌ سرویس مورد نظر یافت نشد.")
                return

            # Create user in Marzban
            result = await self.create_marzban_user(user.username, {
                'duration': service.duration,
                'data_limit': service.data_limit,
                'inbound_id': service.inbound_id
            })

            if result['success']:
                # Deduct the price from user's wallet balance)
                self.db.update_user_balance(update.effective_user.id, -service.price)

                # Log the transaction
                self.db.create_transaction(
                    user_id=user.id,
                    amount=service.price,
                    type_='purchase',
                    status='completed'
                )


                #create service for user
                self.db.create_user_service(
                    user_id=user.id,
                    service_id=service.id,
                    marzban_username=str(service.inbound_id),
                    expire_date=datetime.utcnow() + timedelta(days=service.duration),
                    data_limit=service.data_limit)

                await query.edit_message_text(
                    f"✅ خرید موفقیت‌آمیز بود!\n\n"
                    f"نام سرویس: {service.name}\n"
                    f"مدت: {service.duration} روز\n"
                    f"حجم: {service.data_limit} GB\n"
                    f"💰 مبلغ: {service.price:,} تومان"
                )
            else:
                await query.edit_message_text("❌ خطا در ایجاد حساب کاربری در پنل Marzban.")

        except ValueError:
            logger.error("Invalid service ID.")
            await query.edit_message_text("❌ خطا در پردازش درخواست. لطفاً مجدداً تلاش کنید.")
        except Exception as e:
            logger.error(f"Error in handle_purchase_confirmation: {e}")
            await query.edit_message_text("❌ خطا در تایید خرید. لطفاً با پشتیبانی تماس بگیرید.")

    async def handle_purchase_confirmation(self, update: Update, context: CallbackContext):
        """Handle purchase confirmation"""
        try:
            query = update.callback_query

            user = self.db.get_user(update.effective_user.id)
            service = self.db.get_service(query.data.split('_')[2])

            if not service:
                await query.edit_message_text("❌ سرویس مورد نظر یافت نشد.")
                return

            # Create user in Marzban
            result = await self.create_marzban_user(user.username, {
                'duration': service.duration,
                'data_limit': service.data_limit,
                'inbound_id': service.inbound_id
            })

            if result['success']:
                # Deduct the price from user's wallet balance)
                self.db.update_user_balance(update.effective_user.id, -service.price)

                # Log the transaction
                self.db.create_transaction(
                    user_id=user.id,
                    amount=service.price,
                    type_='purchase',
                    status='completed'
                )

                #create service for user
                self.db.create_user_service(
                    user_id=user.id,
                    service_id=service.id,
                    marzban_username=str(service.inbound_id),
                    expire_date=datetime.utcnow() + timedelta(days=service.duration),
                    data_limit=service.data_limit)

                await query.edit_message_text(
                    f"✅ خرید موفقیت‌آمیز بود!\n\n"
                    f"نام سرویس: {service.name}\n"
                    f"مدت: {service.duration} روز\n"
                    f"حجم: {service.data_limit} GB\n"
                    f"💰 مبلغ: {service.price:,} تومان"
                )
            else:
                await query.edit_message_text("❌ خطا در ایجاد حساب کاربری در پنل Marzban.")

        except ValueError:
            logger.error("Invalid service ID.")
            await query.edit_message_text("❌ خطا در پردازش درخواست. لطفاً مجدداً تلاش کنید.")
        except Exception as e:
            logger.error(f"Error in handle_purchase_confirmation: {e}")
            await query.edit_message_text("❌ خطا در تایید خرید. لطفاً با پشتیبانی تماس بگیرید.")

    async def handle_wallet_charge(self, update: Update, context: CallbackContext):
        """Handle wallet charge request"""
        try:
            query = update.callback_query

            amounts = [50000, 100000, 200000, 500000]
            keyboard = []

            for amount in amounts:
                keyboard.append([
                    InlineKeyboardButton(
                        f"💰 {amount:,} تومان",
                        callback_data=f'charge_{amount}'
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "💳 لطفا مبلغ شارژ کیف پول را انتخاب کنید:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in handle_wallet_charge: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در پردازش درخواست. لطفاً مجدداً تلاش کنید."
            )

    async def process_payment(self, update: Update, context: CallbackContext):
        """Process payment for wallet charge"""
        try:
            query = update.callback_query
            amount = int(query.data.split('_')[1])

            # Get random card number
            card_number = PAYMENT_METHODS["card"]["numbers"][0]
            card_holder = PAYMENT_METHODS["card"]["name"]

            # Create pending transaction
            user = self.db.get_user(update.effective_user.id)
            transaction_id = self.db.create_transaction(
                user_id=user.id,
                amount=amount,
                type_='deposit',
                status='pending'
            )

            text = f"""
💳 اطلاعات پرداخت:
مبلغ: {amount:,} تومان
شماره کارت: `{card_number}`
به نام: {card_holder}

پس از واریز، روی دکمه زیر کلیک کنید.
"""

            keyboard = [[
                InlineKeyboardButton("✅ پرداخت انجام شد", callback_data=f'confirm_payment_{transaction_id}_{amount}')
            ]]

            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error in process_payment: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در پردازش درخواست. لطفاً مجدداً تلاش کنید."
            )

    async def handle_payment_confirmation(self, update: Update, context: CallbackContext):
        """Handle payment confirmation"""
        try:
            query = update.callback_query
            transaction_id, amount = map(int, query.data.split('_')[2:])

            # Update transaction status
            self.db.update_transaction_status(transaction_id, 'completed')

            # Get user and update balance
            self.db.update_user_balance(update.effective_user.id, amount)

            await query.edit_message_text(
                "✅ پرداخت شما با موفقیت انجام شد و کیف پول شما شارژ شد.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]
                ])
            )

        except Exception as e:
            logger.error(f"Error in handle_payment_confirmation: {e}")
            await query.edit_message_text(
                "❌ خطا در تایید پرداخت. لطفاً با پشتیبانی تماس بگیرید."
            )

    async def show_admin_panel(self, update: Update, context: CallbackContext):
        """Show admin panel"""
        try:
            if update.effective_user.id != ADMIN_ID:
                return

            keyboard = [
                [InlineKeyboardButton("📊 گزارش فروش", callback_data='admin_sales_report')],
                [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='admin_users')],
                [InlineKeyboardButton("🎁 کد تخفیف", callback_data='admin_discount_codes')],
                [InlineKeyboardButton("📨 ارسال پیام همگانی", callback_data='admin_broadcast')],
                [InlineKeyboardButton("⚙️ تنظیمات سرویس‌ها", callback_data='admin_services')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(
                "⚙️ پنل مدیریت\nلطفا یک گزینه را انتخاب کنید:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in show_admin_panel: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در نمایش پنل مدیریت. لطفاً مجدداً تلاش کنید."
            )

    async def show_sales_report(self, update: Update, context: CallbackContext):
        """Show sales report"""
        if update.effective_user.id != ADMIN_ID:
            return

        with Session(self.db.engine) as session:
            # Daily sales
            today = datetime.utcnow().date()
            daily_sales = session.query(Transaction).filter(
                Transaction.type == 'purchase',
                Transaction.status == 'completed',
                Transaction.created_at >= today
            ).all()

            # Weekly sales
            week_ago = today - timedelta(days=7)
            weekly_sales = session.query(Transaction).filter(
                Transaction.type == 'purchase',
                Transaction.status == 'completed',
                Transaction.created_at >= week_ago
            ).all()

            # Monthly sales
            month_ago = today - timedelta(days=30)
            monthly_sales = session.query(Transaction).filter(
                Transaction.type == 'purchase',
                Transaction.status == 'completed',
                Transaction.created_at >= month_ago
            ).all()

            report = f"""
📊 گزارش فروش:

امروز:
تعداد: {len(daily_sales)}
مبلغ: {sum(t.amount for t in daily_sales):,} تومان

هفته اخیر:
تعداد: {len(weekly_sales)}
مبلغ: {sum(t.amount for t in weekly_sales):,} تومان

ماه اخیر:
تعداد: {len(monthly_sales)}
مبلغ: {sum(t.amount for t in monthly_sales):,} تومان
"""

            keyboard = [
                [InlineKeyboardButton("📈 گزارش تفصیلی", callback_data='detailed_report')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(report, reply_markup=reply_markup)

    async def manage_users(self, update: Update, context: CallbackContext):
        """Manage users"""
        if update.effective_user.id != ADMIN_ID:
            return

        with Session(self.db.engine) as session:
            # Get users statistics
            total_users = session.query(User).count()
            active_users = session.query(User).join(UserService).filter(
                UserService.is_active == True
            ).distinct().count()

            text = f"""
👥 مدیریت کاربران

کل کاربران: {total_users}
کاربران فعال: {active_users}

برای مدیریت کاربران از گزینه‌های زیر استفاده کنید:
"""

            keyboard = [
                [InlineKeyboardButton("📊 کاربران فعال", callback_data='active_users')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def show_active_users(self, update: Update, context: CallbackContext):
        """Show active users"""
        with Session(self.db.engine) as session:
            active_users = session.query(User).join(UserService).filter(
                UserService.is_active == True
            ).distinct().all()

            if not active_users:
                await update.callback_query.edit_message_text("❌ هیچ کاربر فعالی یافت نشد.")
                return

            text = "📋 کاربران فعال:\n"
            for user in active_users:
                text += f"👤 {user.username} - ID: {user.telegram_id}\n"

            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به مدیریت کاربران", callback_data='admin_users')]
             ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(text)

    async def broadcast_message(self, update: Update, context: CallbackContext):
        """Send broadcast message to users"""
        if update.effective_user.id != ADMIN_ID:
            return

        keyboard = [
            # [InlineKeyboardButton("👥 همه کاربران", callback_data='broadcast_all')],
            # [InlineKeyboardButton("✅ کاربران فعال", callback_data='broadcast_active')],
            # [InlineKeyboardButton("❌ کاربران غیرفعال", callback_data='broadcast_inactive')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = "📨 ارسال پیام همگانی\n\nلطفا متن پیام خود را وارد کنید:"
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message_text,
                    reply_markup=reply_markup
                )
            elif update.message:
                await update.message.reply_text(
                    message_text,
                    reply_markup=reply_markup
                )
            else:
                logger.error("No callback query or message found in the update.")
                return

            context.user_data['admin_state'] = 'waiting_broadcast_message'
        except Exception as e:
            logger.error(f"Error in broadcast_message: {e}")
            await update.message.reply_text("خطا در پردازش درخواست. لطفا دوباره امتحان کنید.")

    async def handle_broadcast_message(self, update: Update, context: CallbackContext):
        """Handle broadcast message text and send to the selected group"""
        if update.effective_user.id != ADMIN_ID:
            return

        # Check if the message exists and has text
        if not update.message or not update.message.text:
            logger.error("No text found in the message.")
            return

        message = update.message.text
        target = context.user_data.get('broadcast_target', 'all')


        with Session(self.db.engine) as session:
            if target == 'all':
                users = session.query(User).all()
            elif target == 'active':
                users = session.query(User).join(UserService).filter(
                    UserService.is_active == True
                ).distinct().all()
            else:  # 'inactive'
                users = session.query(User).outerjoin(UserService).filter(
                    UserService.id == None
                ).all()

            success, failed = 0, 0

            for user in users:
                try:
                    await context.bot.send_message(user.telegram_id, message)
                    success += 1
                except Exception as e:
                    logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
                    failed += 1

            await update.message.reply_text(
                f"📨 پیام همگانی ارسال شد:\n"
                f"✅ موفق: {success}\n"
                f"❌ ناموفق: {failed}"
            )

        # Clear the state after sending
        context.user_data.pop('admin_state', None)
        context.user_data.pop('broadcast_target', None)


    async def manage_services(self, update: Update, context: CallbackContext):
        """Manage services settings"""
        if update.effective_user.id != ADMIN_ID:
            return

        #TODO handle each key sepratedly
        keyboard = [
            [InlineKeyboardButton("➕ افزودن سرویس", callback_data='add_service')],
            [InlineKeyboardButton("📝 ویرایش سرویس‌ها", callback_data='edit_services')],
            [InlineKeyboardButton("🔄 تنظیمات تمدید", callback_data='renewal_settings')],
            [InlineKeyboardButton("⚙️ تنظیمات اینباند", callback_data='inbound_settings')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "⚙️ مدیریت سرویس‌ها و تنظیمات\nلطفا یک گزینه را انتخاب کنید:",
            reply_markup=reply_markup
        )

    async def add_service(self, update: Update, context: CallbackContext):
        #TODO
        """Start adding new service"""
        if update.effective_user.id != ADMIN_ID:
            return

        context.user_data['admin_state'] = 'adding_service_name'
        await update.callback_query.edit_message_text(
            "لطفا نام سرویس جدید را وارد کنید:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 انصراف", callback_data='manage_services')
            ]])
        )


    async def handle_service_input(self, update: Update, context: CallbackContext):
        """Handle service creation input"""
        if update.effective_user.id != ADMIN_ID:
            return

        state = context.user_data.get('admin_state', '')
        if not state.startswith('adding_service_'):
            return

        if state == 'adding_service_name':
            context.user_data['new_service'] = {'name': update.message.text}
            context.user_data['admin_state'] = 'adding_service_price'
            await update.message.reply_text("لطفا قیمت سرویس را به تومان وارد کنید:")

        elif state == 'adding_service_price':
            try:
                price = int(update.message.text)
                context.user_data['new_service']['price'] = price
                context.user_data['admin_state'] = 'adding_service_duration'
                await update.message.reply_text("لطفا مدت زمان سرویس را به روز وارد کنید:")
            except ValueError:
                await update.message.reply_text("لطفا یک عدد صحیح وارد کنید.")

        elif state == 'adding_service_duration':
            try:
                duration = int(update.message.text)
                context.user_data['new_service']['duration'] = duration
                context.user_data['admin_state'] = 'adding_service_data_limit'
                await update.message.reply_text("لطفا حجم سرویس را به گیگابایت وارد کنید:")
            except ValueError:
                await update.message.reply_text("لطفا یک عدد صحیح وارد کنید.")

        elif state == 'adding_service_data_limit':
            try:
                data_limit = float(update.message.text)
                new_service = context.user_data['new_service']
                new_service['data_limit'] = data_limit
                new_service['is_active'] = True
                new_service['inbound_id'] = 1  # Default inbound ID

                with Session(self.db.engine) as session:
                    service = Service(**new_service)
                    session.add(service)
                    session.commit()

                await update.message.reply_text(
                    f"✅ سرویس جدید با موفقیت اضافه شد:\n\n"
                    f"نام: {new_service['name']}\n"
                    f"قیمت: {new_service['price']:,} تومان\n"
                    f"مدت: {new_service['duration']} روز\n"
                    f"حجم: {new_service['data_limit']} GB"
                )

                context.user_data.pop('admin_state', None)
                context.user_data.pop('new_service', None)

            except ValueError:
                await update.message.reply_text("لطفا یک عدد صحیح یا اعشاری وارد کنید.")

    async def edit_services(self, update: Update, context: CallbackContext):
        """Show services for editing"""
        if update.effective_user.id != ADMIN_ID:
            return

        with Session(self.db.engine) as session:
            services = session.query(Service).all()
            keyboard = []

            for service in services:
                status = "✅" if service.is_active else "❌"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status} {service.name} - {service.price:,} تومان",
                        callback_data=f'edit_service_details_{service.id}'
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_services')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                "📝 لیست سرویس‌ها:\nبرای ویرایش روی سرویس مورد نظر کلیک کنید:",
                reply_markup=reply_markup
            )


    async def edit_service_details(self, update: Update, context: CallbackContext):
        """Show service editing options"""
        if update.effective_user.id != ADMIN_ID:
            return

        query = update.callback_query

        try:
            # Extract service_id from callback_data
            service_id = int(query.data.split('_')[-1])  # Get the last part of the callback_data
        except (IndexError, ValueError):
            await query.edit_message_text("❌ خطا در دریافت اطلاعات سرویس.")
            return

        with Session(self.db.engine) as session:
            service = session.query(Service).filter_by(id=service_id).first()
            if not service:
                await query.edit_message_text("❌ سرویس مورد نظر یافت نشد.")
                return

            status = "فعال ✅" if service.is_active else "غیرفعال ❌"
            text = f"""
    🔧 ویرایش سرویس:
    نام: {service.name}
    قیمت: {service.price:,} تومان
    مدت: {service.duration} روز
    حجم: {service.data_limit} GB
    وضعیت: {status}
    """
            keyboard = [
                [InlineKeyboardButton("📝 ویرایش نام", callback_data=f'edit_service_name_{service_id}')],
                [InlineKeyboardButton("💰 ویرایش قیمت", callback_data=f'edit_service_price_{service_id}')],
                [InlineKeyboardButton("⏱ ویرایش مدت", callback_data=f'edit_service_duration_{service_id}')],
                [InlineKeyboardButton("📊 ویرایش حجم", callback_data=f'edit_service_data_limit_{service_id}')],
                [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data=f'toggle_service_{service_id}')],
                [InlineKeyboardButton("❌ حذف سرویس", callback_data=f'delete_service_{service_id}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='edit_services')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
            
    async def edit_service_name(self, update: Update, context: CallbackContext):
        """Save the updated service name"""

        if update.effective_user.id != ADMIN_ID:
            print("im here")
            return
        
        new_name = update.message.text.strip()

        if not new_name:
            await update.message.reply_text("❌ نام سرویس نمی‌تواند خالی باشد.")
            return

        service_id = context.user_data.get('edit_service_id')
        if not service_id:
            await update.message.reply_text("❌ خطا در دریافت اطلاعات سرویس.")
            return

        with Session(self.db.engine) as session:
            service = session.query(Service).filter_by(id=service_id).first()
            if not service:
                await update.message.reply_text("❌ سرویس مورد نظر یافت نشد.")
                return

            # Update the service name
            service.name = new_name
            session.commit()

        await update.message.reply_text(f"✅ نام سرویس به '{new_name}' تغییر یافت.")
        context.user_data.pop('edit_service_id', None)
        context.user_data.pop('edit_field', None)
    
    async def edit_service_price(self, update: Update, context: CallbackContext):
        """Handle editing service price"""
        query = update.callback_query
        service_id = int(query.data.split('_')[-1])

        # Store service_id in context for later use
        context.user_data['edit_service_id'] = service_id
        context.user_data['edit_field'] = 'price'

        await query.edit_message_text("لطفا قیمت جدید سرویس را وارد کنید:")
    
    async def edit_service_duration(self, update: Update, context: CallbackContext):
        """Handle editing service duration"""
        query = update.callback_query
        service_id = int(query.data.split('_')[-1])

        # Store service_id in context for later use
        context.user_data['edit_service_id'] = service_id
        context.user_data['edit_field'] = 'duration'

        await query.edit_message_text("لطفا مدت جدید سرویس را وارد کنید (روز):")
    
    async def edit_service_data_limit(self, update: Update, context: CallbackContext):
        """Handle editing service data limit"""
        query = update.callback_query
        service_id = int(query.data.split('_')[-1])

        # Store service_id in context for later use
        context.user_data['edit_service_id'] = service_id
        context.user_data['edit_field'] = 'data_limit'

        await query.edit_message_text("لطفا حجم جدید سرویس را وارد کنید (GB):")
    
    async def toggle_service(self, update: Update, context: CallbackContext):
        """Handle toggling service status"""
        query = update.callback_query
        service_id = int(query.data.split('_')[-1])

        with Session(self.db.engine) as session:
            service = session.query(Service).filter_by(id=service_id).first()
            if not service:
                await query.edit_message_text("❌ سرویس مورد نظر یافت نشد.")
                return

            # Toggle the service status
            service.is_active = not service.is_active
            session.commit()

            status = "فعال ✅" if service.is_active else "غیرفعال ❌"
            await query.edit_message_text(f"وضعیت سرویس به {status} تغییر یافت.")
        
    async def delete_service(self, update: Update, context: CallbackContext):
        """Handle deleting a service"""
        query = update.callback_query
        service_id = int(query.data.split('_')[-1])

        with Session(self.db.engine) as session:
            service = session.query(Service).filter_by(id=service_id).first()
            if not service:
                await query.edit_message_text("❌ سرویس مورد نظر یافت نشد.")
                return

            # Delete the service
            session.delete(service)
            session.commit()

            await query.edit_message_text("✅ سرویس با موفقیت حذف شد.")
        
        
    
    async def renewal_settings(self, update: Update, context: CallbackContext):
        """Manage renewal settings for a service"""
        if update.effective_user.id != ADMIN_ID:
            return

        try:
            # Retrieve active services from the database
            services = self.db.get_active_services()
            if not services:
                await update.callback_query.edit_message_text("❌ هیچ سرویسی برای تمدید یافت نشد.")
                return

            # Create a keyboard to list services
            keyboard = [
                [InlineKeyboardButton(f"{service.name} - {service.price:,} تومان", callback_data=f'renew_{service.id}')]
                for service in services
            ]
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                "⚙️ لطفا سرویس مورد نظر برای تمدید را انتخاب کنید:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in renewal settings: {e}")
            await update.callback_query.edit_message_text("❌ خطا در دریافت اطلاعات سرویس‌ها.")

    async def manage_discount_codes(self, update: Update, context: CallbackContext):
        """Manage discount codes"""
        if update.effective_user.id != ADMIN_ID:
            return

        keyboard = [
            [InlineKeyboardButton("➕ کد تخفیف جدید", callback_data='add_discount')],
            [InlineKeyboardButton("📋 لیست کدهای تخفیف", callback_data='list_discount_codes')], #TODO: create this call_back
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "🎁 مدیریت کدهای تخفیف\nلطفا یک گزینه را انتخاب کنید:",
            reply_markup=reply_markup
        )

    async def list_discount_codes(self, update: Update, context: CallbackContext):
        """Show list of discount codes"""
        if update.effective_user.id != ADMIN_ID:
            return

        with Session(self.db.engine) as session:
            discount_codes = session.query(DiscountCode).all()

            if not discount_codes:
                await update.callback_query.edit_message_text("❌ هیچ کد تخفیفی یافت نشد.")
                return

            text = "📋 لیست کدهای تخفیف:\n"
            for code in discount_codes:
                status = "✅ فعال" if code.is_active else "❌ غیرفعال"
                text += f"💳 کد: {code.code} - نوع: {code.type} - مقدار: {code.amount} - وضعیت: {status}\n"

            await update.callback_query.edit_message_text(text)


    async def add_discount_code(self, update: Update, context: CallbackContext):
        #TODO: handle add discount % and static $
        """Start adding new discount code"""
        if update.effective_user.id != ADMIN_ID:
            return

        context.user_data['admin_state'] = 'adding_discount_code'
        await update.callback_query.edit_message_text(
            "لطفا کد تخفیف را وارد کنید:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 انصراف", callback_data='manage_discount_codes')
            ]])
        )

    async def handle_discount_input(self, update: Update, context: CallbackContext):
        """Handle discount code creation input"""
        if update.effective_user.id != ADMIN_ID:
            return

        state = context.user_data.get('admin_state', '')

        if state == 'adding_discount_code':
            context.user_data['new_discount'] = {'code': update.message.text.upper()}
            context.user_data['admin_state'] = 'adding_discount_type'
            keyboard = [
                [InlineKeyboardButton("درصدی", callback_data='discount_type_percent')],
                [InlineKeyboardButton("مبلغ ثابت", callback_data='discount_type_fixed')]
            ]
            await update.message.reply_text("نوع تخفیف را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif state == 'adding_discount_amount':
            user_input = update.message.text.strip()
            new_discount = context.user_data.get('new_discount', {})

            if not new_discount.get('type'):
                await update.message.reply_text("❌ مقدار تخفیف دریافت نشد. لطفاً از ابتدا تلاش کنید.")
                return

            try:
                if new_discount['type'] == 'percent':
                    if not user_input.endswith('%'):
                        await update.message.reply_text("لطفا مقدار تخفیف درصدی را با علامت % وارد کنید.")
                        return
                    amount = float(user_input.rstrip('%'))
                    if not (0 < amount <= 100):
                        await update.message.reply_text("لطفا یک مقدار درصدی بین 0 تا 100 وارد کنید.")
                        return

                elif new_discount['type'] == 'fixed':
                    if not user_input.isdigit():
                        await update.message.reply_text("لطفا مقدار تخفیف ثابت را به عدد وارد کنید.")
                        return
                    amount = float(user_input)
                    if amount <= 0:
                        await update.message.reply_text("لطفا یک مقدار مثبت وارد کنید.")
                        return

                with Session(self.db.engine) as session:
                    discount = DiscountCode(
                        code=new_discount['code'],
                        type=new_discount['type'],
                        amount=amount,
                        is_active=True
                    )
                    session.add(discount)
                    session.commit()

                amount_text = f"{amount}%" if new_discount['type'] == 'percent' else f"{amount:,} تومان"
                await update.message.reply_text(
                    f"✅ کد تخفیف با موفقیت اضافه شد:\n\n"
                    f"کد: {new_discount['code']}\n"
                    f"نوع: {'درصدی' if new_discount['type'] == 'percent' else 'مبلغ ثابت'}\n"
                    f"مقدار: {amount_text}"
                )

                context.user_data.pop('admin_state', None)
                context.user_data.pop('new_discount', None)

            except ValueError:
                await update.message.reply_text("❌ لطفا یک مقدار معتبر وارد کنید.")

    async def handle_discount_type(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()
        new_discount = context.user_data.get('new_discount', {})

        if query.data == 'discount_type_percent':
            new_discount['type'] = 'percent'
            await query.edit_message_text("لطفا مقدار تخفیف درصدی را وارد کنید (مثال: 20%)")
        elif query.data == 'discount_type_fixed':
            new_discount['type'] = 'fixed'
            await query.edit_message_text("لطفا مقدار تخفیف ثابت را به تومان وارد کنید (مثال: 50000)")
        else:
            await query.message.reply_text("❌ نوع تخفیف نامعتبر است. لطفا دوباره تلاش کنید.")
            return

        context.user_data['new_discount'] = new_discount
        context.user_data['admin_state'] = 'adding_discount_amount'


    async def manage_transactions(self, update: Update, context: CallbackContext):
        """Show transaction management options"""
        if update.effective_user.id != ADMIN_ID:
            return

        keyboard = [
            [InlineKeyboardButton("💰 تراکنش‌های در انتظار", callback_data='pending_transactions')],
            [InlineKeyboardButton("📊 گزارش تراکنش‌ها", callback_data='transaction_report')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "💳 مدیریت تراکنش‌ها\nلطفا یک گزینه را انتخاب کنید:",
            reply_markup=reply_markup
        )

    async def show_pending_transactions(self, update: Update, context: CallbackContext):
        """Show pending transactions"""
        if update.effective_user.id != ADMIN_ID:
            return

        with Session(self.db.engine) as session:
            transactions = session.query(Transaction).filter_by(
                status='pending'
            ).order_by(Transaction.created_at.desc()).all()

            if not transactions:
                await update.callback_query.edit_message_text(
                    "هیچ تراکنش در انتظاری وجود ندارد.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data='manage_transactions')
                    ]])
                )
                return

            for transaction in transactions:
                user = session.query(User).filter_by(id=transaction.user_id).first()
                keyboard = [
                    [
                        InlineKeyboardButton("✅ تایید", callback_data=f'approve_transaction_{transaction.id}'),
                        InlineKeyboardButton("❌ رد", callback_data=f'reject_transaction_{transaction.id}')
                    ]
                ]

                await context.bot.send_message(
                    update.effective_user.id,
                    f"""
💳 تراکنش جدید:
👤 کاربر: {user.username or user.telegram_id}
💰 مبلغ: {transaction.amount:,} تومان
⏰ زمان: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                    """,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

    async def handle_transaction_action(self, update: Update, context: CallbackContext):
        """Handle transaction approval/rejection"""
        if update.effective_user.id != ADMIN_ID:
            return

        query = update.callback_query
        action, transaction_id = query.data.split('_')[1:]
        transaction_id = int(transaction_id)

        with Session(self.db.engine) as session:
            transaction = session.query(Transaction).filter_by(id=transaction_id).first()
            if not transaction or transaction.status != 'pending':
                await query.edit_message_text("❌ تراکنش مورد نظر یافت نشد یا قبلا بررسی شده است.")
                return

            user = session.query(User).filter_by(id=transaction.user_id).first()

            if action == 'approve':
                transaction.status = 'completed'
                user.wallet_balance += transaction.amount
                message = f"✅ تراکنش شما به مبلغ {transaction.amount:,} تومان تایید و کیف پول شما شارژ شد."
            else:
                transaction.status = 'rejected'
                message = f"❌ تراکنش شما به مبلغ {transaction.amount:,} تومان رد شد."

            session.commit()

            # Notify user
            try:
                await context.bot.send_message(user.telegram_id, message)
            except Exception as e:
                logger.error(f"Failed to notify user {user.telegram_id}: {e}")

            await query.edit_message_text("✅ عملیات با موفقیت انجام شد.")

    async def setup_notifications(self):
        """Setup automatic notifications"""
        while True:
            try:
                await self.check_expiring_services()
                await self.check_low_data_services()
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                logger.error(f"Error in notifications: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def check_expiring_services(self):
        """Check and notify users about expiring services"""
        with Session(self.db.engine) as session:
            # Get services expiring in SUBSCRIPTION_REMINDER_DAYS
            expiring_date = datetime.utcnow() + timedelta(days=SUBSCRIPTION_REMINDER_DAYS)
            services = session.query(UserService).filter(
                UserService.is_active == True,
                UserService.expire_date <= expiring_date,
                UserService.expire_date > datetime.utcnow()
            ).all()

            for service in services:
                days_left = (service.expire_date - datetime.utcnow()).days
                try:
                    await self.bot.send_message(
                        service.user.telegram_id,
                        f"""
⚠️ اخطار انقضای سرویس:
سرویس {service.service.name} شما تا {days_left} روز دیگر منقضی می‌شود.
برای تمدید سرویس از منوی اصلی اقدام کنید.
                        """
                    )
                except Exception as e:
                    logger.error(f"Failed to send expiry notification: {e}")

    async def check_low_data_services(self):
        """Check and notify users about low data services"""
        with Session(self.db.engine) as session:
            active_services = session.query(UserService).filter(
                UserService.is_active == True
            ).all()

            for service in active_services:
                remaining_gb = (service.data_limit - service.data_used) / 1024
                if remaining_gb <= SUBSCRIPTION_REMINDER_DATA:
                    try:
                        await self.bot.send_message(
                            service.user.telegram_id,
                            f"""
⚠️ اخطار اتمام حجم:
حجم باقیمانده سرویس {service.service.name} شما {remaining_gb:.1f} GB است.
برای خرید حجم اضافه از منوی اصلی اقدام کنید.
                        """
                        )
                    except Exception as e:
                        logger.error(f"Failed to send data limit notification: {e}")

    async def manage_inbounds(self, update: Update, context: CallbackContext):
        """Manage inbound settings"""
        if update.effective_user.id != ADMIN_ID:
            return

        try:
            inbounds = await self.marzban.get_inbounds()
            keyboard = []

            for inbound in inbounds:
                status = "✅" if inbound["enable"] else "❌"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status} {inbound['tag']} - پورت: {inbound['port']}",
                        callback_data=f'inbound_{inbound["id"]}'
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_services')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                "⚙️ مدیریت اینباندها\nبرای تغییر تنظیمات روی اینباند مورد نظر کلیک کنید:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error getting inbounds: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در دریافت اطلاعات اینباندها"
            )

    async def edit_inbound(self, update: Update, context: CallbackContext):
        """Show inbound editing options"""
        if update.effective_user.id != ADMIN_ID:
            return

        query = update.callback_query
        inbound_id = int(query.data.split('_')[1])

        try:
            inbound = await self.marzban.get_inbound(inbound_id)
            status = "فعال ✅" if inbound["enable"] else "غیرفعال ❌"

            text = f"""
🔧 ویرایش اینباند:
نام: {inbound['tag']}
پورت: {inbound['port']}
پروتکل: {inbound['protocol']}
وضعیت: {status}
            """

            keyboard = [
                [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data=f'toggle_inbound_{inbound_id}')],
                [InlineKeyboardButton("📝 ویرایش پورت", callback_data=f'edit_inbound_port_{inbound_id}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='manage_inbounds')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error getting inbound details: {e}")
            await query.edit_message_text("❌ خطا در دریافت اطلاعات اینباند")

    async def toggle_inbound(self, update: Update, context: CallbackContext):
        """Toggle inbound status"""
        if update.effective_user.id != ADMIN_ID:
            return

        query = update.callback_query
        inbound_id = int(query.data.split('_')[2])

        try:
            inbound = await self.marzban.get_inbound(inbound_id)
            new_status = not inbound["enable"]

            await self.marzban.update_inbound(inbound_id, {"enable": new_status})

            status_text = "فعال ✅" if new_status else "غیرفعال ❌"
            await query.edit_message_text(
                f"✅ وضعیت اینباند {inbound['tag']} به {status_text} تغییر کرد."
            )

        except Exception as e:
            logger.error(f"Error toggling inbound: {e}")
            await query.edit_message_text("❌ خطا در تغییر وضعیت اینباند")

    async def detailed_report(self, update: Update, context: CallbackContext):
        """Show detailed report options"""
        if update.effective_user.id != ADMIN_ID:
            return

        keyboard = [
            [InlineKeyboardButton("📊 گزارش روزانه", callback_data='report_daily')],
            [InlineKeyboardButton("📈 گزارش هفتگی", callback_data='report_weekly')],
            [InlineKeyboardButton("📉 گزارش ماهانه", callback_data='report_monthly')],
            [InlineKeyboardButton("🗓 گزارش سفارشی", callback_data='report_custom')],
            [InlineKeyboardButton("💾 ذخیره گزارش", callback_data='save_report')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "📊 گزارش‌گیری تفصیلی\nلطفا نوع گزارش را انتخاب کنید:",
            reply_markup=reply_markup
        )

    async def generate_report(self, start_date: datetime, end_date: datetime):
        """Generate detailed report for given period"""
        with Session(self.db.engine) as session:
            # Sales data
            sales = session.query(Transaction).filter(
                Transaction.type == 'purchase',
                Transaction.status == 'completed',
                Transaction.created_at.between(start_date, end_date)
            ).all()

            # User statistics
            new_users = session.query(User).filter(
                User.created_at.between(start_date, end_date)
            ).count()

            active_services = session.query(UserService).filter(
                UserService.is_active == True,
                UserService.created_at <= end_date,
                UserService.expire_date > end_date
            ).count()

            # Most popular services
            service_stats = {}
            for sale in sales:
                service = session.query(UserService).filter_by(
                    user_id=sale.user_id,
                    created_at=sale.created_at
                ).first()
                if service:
                    service_name = service.service.name
                    service_stats[service_name] = service_stats.get(service_name, 0) + 1

            report = {
                'period': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d')
                },
                'sales': {
                    'total': sum(s.amount for s in sales),
                    'count': len(sales)
                },
                'users': {
                    'new': new_users,
                    'active_services': active_services
                },
                'popular_services': service_stats
            }

            return report

    async def show_report(self, update: Update, context: CallbackContext):
        """Show generated report"""
        query = update.callback_query
        report_type = query.data.split('_')[1]

        end_date = datetime.utcnow()
        if report_type == 'daily':
            start_date = end_date - timedelta(days=1)
        elif report_type == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif report_type == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            # Handle custom date range
            context.user_data['report_state'] = 'waiting_start_date'
            await query.edit_message_text(
                "لطفا تاریخ شروع را به فرمت YYYY-MM-DD وارد کنید:"
            )
            return

        report = await self.generate_report(start_date, end_date)

        text = f"""
📊 گزارش {report_type}:
از تاریخ {report['period']['start']} تا {report['period']['end']}

💰 فروش:
• مجموع: {report['sales']['total']:,} تومان
• تعداد: {report['sales']['count']} تراکنش

👥 کاربران:
• جدید: {report['users']['new']} کاربر
• سرویس‌های فعال: {report['users']['active_services']}

🔝 محبوب‌ترین سرویس‌ها:
"""
        for service, count in sorted(
            report['popular_services'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            text += f"• {service}: {count} فروش\n"

        keyboard = [
            [InlineKeyboardButton("💾 ذخیره گزارش", callback_data=f'save_report_{report_type}')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='detailed_report')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def manage_backups(self, update: Update, context: CallbackContext):
        """Show backup management options"""
        if update.effective_user.id != ADMIN_ID:
            return

        keyboard = [
            [InlineKeyboardButton("📦 پشتیبان‌گیری کامل", callback_data='backup_full')],
            [InlineKeyboardButton("👥 پشتیبان کاربران", callback_data='backup_users')],
            [InlineKeyboardButton("🔄 پشتیبان سرویس‌ها", callback_data='backup_services')],
            [InlineKeyboardButton("💳 پشتیبان تراکنش‌ها", callback_data='backup_transactions')],
            [InlineKeyboardButton("📋 لیست پشتیبان‌ها", callback_data='list_backups')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "💾 مدیریت نسخه‌های پشتیبان\nلطفا یک گزینه را انتخاب کنید:",
            reply_markup=reply_markup
        )

    async def create_backup(self, backup_type: str):
        """Create backup of specified type"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_{backup_type}_{timestamp}.json"

            with Session(self.db.engine) as session:
                data = {}

                if backup_type in ['full', 'users']:
                    users = session.query(User).all()
                    data['users'] = [
                        {
                            'telegram_id': user.telegram_id,
                            'username': user.username,
                            'wallet_balance': user.wallet_balance,
                            'is_admin': user.is_admin,
                            'created_at': user.created_at.isoformat()
                        }
                        for user in users
                    ]

                if backup_type in ['full', 'services']:
                    services = session.query(Service).all()
                    data['services'] = [
                        {
                            'name': service.name,
                            'price': service.price,
                            'duration': service.duration,
                            'data_limit': service.data_limit,
                            'is_active': service.is_active,
                            'inbound_id': service.inbound_id
                        }
                        for service in services
                    ]

                if backup_type in ['full', 'transactions']:
                    transactions = session.query(Transaction).all()
                    data['transactions'] = [
                        {
                            'user_id': tx.user_id,
                            'amount': tx.amount,
                            'type': tx.type,
                            'status': tx.status,
                            'created_at': tx.created_at.isoformat()
                        }
                        for tx in transactions
                    ]

                # Save backup file
                with open(f'backups/{filename}', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Create backup record
                backup = Backup(
                    filename=filename,
                    size=os.path.getsize(f'backups/{filename}'),
                    type=backup_type,
                    status='completed'
                )
                session.add(backup)
                session.commit()

                return backup

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            with Session(self.db.engine) as session:
                backup = Backup(
                    filename=filename,
                    type=backup_type,
                    status='failed',
                    note=str(e)
                )
                session.add(backup)
                session.commit()
            raise

    async def handle_backup(self, update: Update, context: CallbackContext):
        """Handle backup creation request"""
        if update.effective_user.id != ADMIN_ID:
            return

        query = update.callback_query
        backup_type = query.data.split('_')[1]

        await query.edit_message_text("⏳ در حال تهیه نسخه پشتیبان...")

        try:
            backup = await self.create_backup(backup_type)

            # Send backup file to admin
            with open(f'backups/{backup.filename}', 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_user.id,
                    document=f,
                    caption=f"""
✅ نسخه پشتیبان با موفقیت ایجاد شد:
📁 نام فایل: {backup.filename}
📊 حجم: {backup.size / 1024:.1f} KB
⏰ زمان: {backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                    """
                )

        except Exception as e:
            await query.edit_message_text(f"❌ خطا در تهیه نسخه پشتیبان: {str(e)}")

    async def list_backups(self, update: Update, context: CallbackContext):
        """Show list of available backups"""
        if update.effective_user.id != ADMIN_ID:
            return

        with Session(self.db.engine) as session:
            backups = session.query(Backup).order_by(Backup.created_at.desc()).limit(10).all()

            if not backups:
                await update.callback_query.edit_message_text(
                    "هیچ نسخه پشتیبانی یافت نشد.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data='manage_backups')
                    ]])
                )
                return

            text = "📋 لیست آخرین نسخه‌های پشتیبان:\n\n"
            keyboard = []

            for backup in backups:
                status = "✅" if backup.status == 'completed' else "❌"
                text += f"""
{status} {backup.filename}
📊 حجم: {backup.size / 1024:.1f} KB
⏰ تاریخ: {backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
                if backup.status == 'completed':
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📥 دانلود {backup.filename}",
                            callback_data=f'download_backup_{backup.id}'
                        )
                    ])

            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_backups')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def download_backup(self, update: Update, context: CallbackContext):
        """Send backup file to admin"""
        if update.effective_user.id != ADMIN_ID:
            return

        query = update.callback_query
        backup_id = int(query.data.split('_')[2])

        with Session(self.db.engine) as session:
            backup = session.query(Backup).filter_by(id=backup_id).first()

            if not backup or backup.status != 'completed':
                await query.edit_message_text("❌ فایل پشتیبان یافت نشد.")
                return

            try:
                with open(f'backups/{backup.filename}', 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_user.id,
                        document=f,
                        caption=f"📁 {backup.filename}"
                    )
            except Exception as e:
                logger.error(f"Error sending backup file: {e}")
                await query.edit_message_text("❌ خطا در ارسال فایل پشتیبان")

    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle text messages"""
        user_id = update.effective_user.id
        message = update.message.text

        # Handle admin states
        if user_id == ADMIN_ID:
            admin_state = context.user_data.get('admin_state')
            if admin_state:
                if admin_state == 'waiting_broadcast_message':
                    await self.handle_broadcast_message(update, context)
                    return
                elif admin_state.startswith('adding_service_'):
                    await self.handle_service_input(update, context)
                    return
                elif admin_state.startswith('adding_discount_'):
                    await self.handle_discount_input(update, context)
                    return

        # Default response
        await update.message.reply_text(
            "لطفا از دکمه‌های منو استفاده کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_main')]
            ])
        )

    async def back_to_main(self, update: Update, context: CallbackContext):
        """Return to main menu"""
        try:
            user_id = update.effective_user.id

            keyboard = [
                [InlineKeyboardButton("🛒 خرید سرویس", callback_data='buy_service')],
                [InlineKeyboardButton("👤 حساب کاربری", callback_data='user_account')],
                [InlineKeyboardButton("📊 اطلاعات سرویس", callback_data='service_info')]
            ]

            if user_id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data='admin_panel')])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(
                MESSAGES["welcome"],
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in back_to_main: {e}")
            await update.callback_query.edit_message_text(
                "❌ خطا در بازگشت به منوی اصلی. لطفاً مجدداً تلاش کنید."
            )

    async def show_service_info(self, update: Update, context: CallbackContext):
        """Show user's active services information"""
        try:
            user_id = update.effective_user.id
            logger.info(f"Showing service info for user {user_id}")

            user = self.db.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                await update.callback_query.edit_message_text(
                    "❌ اطلاعات کاربری شما یافت نشد."
                )
                return

            logger.info(f"Found user: {user}")
            active_services = self.db.get_user_active_services(user.id)
            logger.info(f"Active services: {active_services}")

            if not active_services:
                text = "❌ شما هیچ سرویس فعالی ندارید."
            else:
                text = "📊 اطلاعات سرویس‌های فعال:\n\n"
                for service in active_services:
                    try:
                        expire_date = service[4]
                        remaining_days = (expire_date - datetime.utcnow()).days
                        remaining_gb = (service[5] - (service[6] or 0)) / 1024  # Convert to GB, handle None

                        text += f"""
🔹 {service[8]}
📅 {remaining_days} روز باقیمانده
📊 {remaining_gb:.1f} GB حجم باقیمانده
💰 {service[9]:,} تومان
──────────────
"""
                    except Exception as e:
                        logger.error(f"Error processing service {service}: {e}")
                        continue

            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in show_service_info: {str(e)}")
            logger.exception(e)  # This will log the full traceback
            await update.callback_query.edit_message_text(
                "❌ خطا در نمایش اطلاعات سرویس. لطفاً مجدداً تلاش کنید."
            )

class CleanupManager:
    def __init__(self, bot: VPNBot):
        self.bot = bot

    async def start_cleanup(self):
        """Start cleanup tasks"""
        while True:
            try:
                await self.cleanup_expired_users()
                await self.cleanup_old_logs()
                await self.cleanup_old_backups()
                await asyncio.sleep(86400)  # Run daily
            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(3600)

    async def cleanup_expired_users(self):
        """Clean up expired users"""
        cleanup_date = datetime.utcnow() - timedelta(days=CLEANUP_SETTINGS["expired_users_days"])

        with Session(self.bot.db.engine) as session:
            expired_services = session.query(UserService).filter(
                UserService.is_active == False,
                UserService.expire_date < cleanup_date
            ).all()

            for service in expired_services:
                try:
                    # Delete from Marzban
                    await self.bot.marzban.delete_user(service.marzban_username)
                except Exception as e:
                    logger.error(f"Error deleting Marzban user: {e}")

                # Delete from database
                session.delete(service)

            session.commit()

    async def cleanup_old_logs(self):
        """Clean up old logs"""
        cleanup_date = datetime.utcnow() - timedelta(days=CLEANUP_SETTINGS["old_logs_days"])

        with Session(self.bot.db.engine) as session:
            # Clean system logs
            session.query(SystemLog).filter(
                SystemLog.created_at < cleanup_date
            ).delete()

            # Clean error logs
            session.query(ErrorLog).filter(
                ErrorLog.created_at < cleanup_date
            ).delete()

            session.commit()

    async def cleanup_old_backups(self):
        """Clean up old backups"""
        cleanup_date = datetime.utcnow() - timedelta(days=CLEANUP_SETTINGS["old_backups_days"])

        with Session(self.bot.db.engine) as session:
            old_backups = session.query(Backup).filter(
                Backup.created_at < cleanup_date
            ).order_by(Backup.created_at.desc())[CLEANUP_SETTINGS["backup_retention_count"]:]

            for backup in old_backups:
                try:
                    # Delete backup file
                    os.remove(f'backups/{backup.filename}')
                    # Delete from database
                    session.delete(backup)
                except Exception as e:
                    logger.error(f"Error deleting backup: {e}")

            session.commit()

class SystemMonitor:
    def __init__(self, bot: VPNBot):
        self.bot = bot

    async def start_monitoring(self):
        """Start system monitoring"""
        while True:
            try:
                await self.check_system_health()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(60)

    async def check_system_health(self):
        """Check various system metrics"""
        try:
            # Check database connection
            with Session(self.bot.db.engine) as session:
                session.query(User).first()

            # Check Marzban connection
            await self.bot.marzban.get_token()

            # Check disk space
            disk_usage = psutil.disk_usage('/')
            if disk_usage.percent > 90:
                await self.bot.log_manager.log(
                    'WARNING',
                    'SystemMonitor',
                    'High disk usage',
                    {'usage_percent': disk_usage.percent}
                )

                # Notify admin
                await self.bot.bot.send_message(
                    ADMIN_ID,
                    f"⚠️ هشدار: فضای دیسک پر شده است ({disk_usage.percent}%)"
                )

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                await self.bot.log_manager.log(
                    'WARNING',
                    'SystemMonitor',
                    'High memory usage',
                    {'usage_percent': memory.percent}
                )

                await self.bot.bot.send_message(
                    ADMIN_ID,
                    f"⚠️ هشدار: مصرف حافظه بالاست ({memory.percent}%)"
                )

        except ClientError as e:
            await self.bot.log_manager.log(
                'ERROR',
                'SystemMonitor',
                'Marzban connection failed',
                {'error': str(e)}
            )
        except Exception as e:
            await self.bot.log_manager.log(
                'ERROR',
                'SystemMonitor',
                'Health check failed',
                {'error': str(e)}
            )
            raise

def main():
    """Start the bot"""
    logging.basicConfig(level=logging.INFO)

    try:
        vpn_bot = VPNBot()

        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", vpn_bot.start))
        application.add_handler(CallbackQueryHandler(vpn_bot.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, vpn_bot.handle_message))

        application.add_error_handler(vpn_bot.error_handler.handle_error)

        print("Bot started successfully!")

        # Run the bot using built-in event loop handling
        application.run_polling()

    except Exception as e:
        logging.error(f"Error starting bot: {e}")

if __name__ == '__main__':
    main()  # No asyncio.run() needed!