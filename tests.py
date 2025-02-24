import unittest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from bot import VPNBot
from database import User, Service, UserService, Transaction
from config import *

class TestVPNBot(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.bot = VPNBot()
        self.loop = asyncio.get_event_loop()
        
    async def async_setup(self):
        """Async setup"""
        await self.bot.initialize()
        
    def test_init(self):
        """Test bot initialization"""
        self.assertIsNotNone(self.bot.engine)
        self.assertIsNotNone(self.bot.marzban)
        
    @patch('bot.VPNBot.create_marzban_user')
    async def test_service_purchase(self, mock_create_user):
        """Test service purchase flow"""
        # Mock data
        user = User(telegram_id=123456, wallet_balance=1000000)
        service = Service(
            name="Test Service",
            price=100000,
            duration=30,
            data_limit=50
        )
        
        # Mock Marzban response
        mock_create_user.return_value = {"username": "test_user"}
        
        # Test purchase
        result = await self.bot.handle_service_purchase(user, service)
        self.assertTrue(result.success)
        self.assertEqual(user.wallet_balance, 900000)
        
    async def test_payment_processing(self):
        """Test payment processing"""
        user = User(telegram_id=123456, wallet_balance=0)
        amount = 100000
        
        # Test payment creation
        transaction = await self.bot.create_payment(user, amount)
        self.assertEqual(transaction.status, 'pending')
        
        # Test payment approval
        await self.bot.approve_payment(transaction)
        self.assertEqual(transaction.status, 'completed')
        self.assertEqual(user.wallet_balance, amount)
        
    def tearDown(self):
        """Clean up after tests"""
        self.loop.close()

if __name__ == '__main__':
    unittest.main() 