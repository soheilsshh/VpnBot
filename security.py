from datetime import datetime, timedelta
from functools import wraps
from telegram import Update
from config import ADMIN_ID, CHANNEL_ID
from advanced_config import SECURITY_SETTINGS
import asyncio
import re

class SecurityManager:
    def __init__(self):
        self.login_attempts = {}
        self.blocked_users = {}
        self.active_sessions = {}
        
    def check_membership(self, update: Update):
        """Check if user is member of required channel"""
        if not SECURITY_SETTINGS["required_membership"]:
            return True
            
        try:
            member = update.bot.get_chat_member(CHANNEL_ID, update.effective_user.id)
            return member.status in ['member', 'administrator', 'creator']
        except:
            return False
    
    def check_login_attempts(self, user_id: int):
        """Check and handle login attempts"""
        if user_id not in self.login_attempts:
            self.login_attempts[user_id] = {'count': 0, 'first_attempt': datetime.utcnow()}
            return True
            
        attempts = self.login_attempts[user_id]
        if attempts['count'] >= SECURITY_SETTINGS["max_login_attempts"]:
            if datetime.utcnow() - attempts['first_attempt'] < timedelta(seconds=SECURITY_SETTINGS["block_time"]):
                self.blocked_users[user_id] = datetime.utcnow()
                return False
            else:
                self.login_attempts[user_id] = {'count': 1, 'first_attempt': datetime.utcnow()}
                return True
                
        attempts['count'] += 1
        return True
    
    def is_blocked(self, user_id: int):
        """Check if user is blocked"""
        if user_id not in self.blocked_users:
            return False
            
        if datetime.utcnow() - self.blocked_users[user_id] > timedelta(seconds=SECURITY_SETTINGS["block_time"]):
            del self.blocked_users[user_id]
            return False
            
        return True

    def validate_input(self, text: str, input_type: str):
        """Validate user input"""
        patterns = {
            'username': r'^[a-zA-Z0-9_]{3,32}$',
            'phone': r'^\+?[0-9]{10,15}$',
            'amount': r'^[0-9]+$',
            'date': r'^\d{4}-\d{2}-\d{2}$'
        }
        
        if input_type not in patterns:
            return False
            
        return bool(re.match(patterns[input_type], text))

def require_membership(func):
    """Decorator to require channel membership"""
    @wraps(func)
    async def wrapper(self, update: Update, context, *args, **kwargs):
        if not self.security_manager.check_membership(update):
            await update.message.reply_text(
                "⚠️ برای استفاده از ربات، لطفا ابتدا در کانال ما عضو شوید."
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper

def admin_only(func):
    """Decorator for admin-only functions"""
    @wraps(func)
    async def wrapper(self, update: Update, context, *args, **kwargs):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔️ دسترسی محدود شده است.")
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper

def rate_limit(calls: int, period: int):
    """Rate limiting decorator"""
    def decorator(func):
        calls_made = {}
        
        @wraps(func)
        async def wrapper(self, update: Update, context, *args, **kwargs):
            user_id = update.effective_user.id
            now = datetime.utcnow()
            
            if user_id in calls_made:
                user_calls = calls_made[user_id]
                # Remove old calls
                user_calls = [call for call in user_calls if now - call < timedelta(seconds=period)]
                
                if len(user_calls) >= calls:
                    await update.message.reply_text(
                        "⚠️ لطفا کمی صبر کنید و سپس مجددا تلاش کنید."
                    )
                    return
                    
                user_calls.append(now)
                calls_made[user_id] = user_calls
            else:
                calls_made[user_id] = [now]
            
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    return decorator 