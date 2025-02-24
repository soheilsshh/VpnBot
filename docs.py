"""
VPN Bot Documentation
====================

This bot provides a complete VPN service management system with the following features:

Core Features:
-------------
1. User Management
2. Service Management
3. Payment Processing
4. Admin Panel
5. Monitoring & Reporting

Installation:
------------
1. Install required packages:
   pip install -r requirements.txt

2. Configure settings in config.py and advanced_config.py

3. Initialize database:
   python init_db.py

4. Run the bot:
   python bot.py

Configuration:
-------------
- BOT_TOKEN: Telegram bot token
- ADMIN_ID: Admin's Telegram ID
- CHANNEL_ID: Required channel ID
- DATABASE_URL: Database connection string
- MARZBAN_CONFIG: Marzban panel settings

Security:
---------
- Channel membership requirement
- Rate limiting
- Input validation
- Session management
- Error handling

Maintenance:
-----------
- Automatic cleanup of expired users
- Log rotation
- Backup management
- Performance monitoring

API Documentation:
----------------
See api_docs.md for detailed API documentation.
"""

# Function documentation examples:
FUNCTION_DOCS = {
    'start': """
    Start command handler
    --------------------
    Initializes user session and shows main menu.
    
    Security:
    - Requires channel membership
    - Rate limited (5 calls per minute)
    - Input validation
    
    Flow:
    1. Check user permissions
    2. Initialize user if new
    3. Show main menu
    """,
    
    'create_service': """
    Create new service
    -----------------
    Creates a new VPN service for user.
    
    Parameters:
    - username: str
    - service_id: int
    
    Returns:
    - service_info: dict
    
    Raises:
    - InsufficientFundsError
    - ServiceCreationError
    """,
    
    # Add more function documentation...
}

# Error codes and messages
ERROR_CODES = {
    'E001': 'Insufficient funds',
    'E002': 'Service creation failed',
    'E003': 'Invalid input',
    'E004': 'Permission denied',
    'E005': 'Rate limit exceeded',
    # Add more error codes...
}

# API endpoints
API_ENDPOINTS = {
    '/api/v1/users': {
        'GET': 'Get user list',
        'POST': 'Create new user',
        'PUT': 'Update user',
        'DELETE': 'Delete user'
    },
    '/api/v1/services': {
        'GET': 'Get service list',
        'POST': 'Create service',
        'PUT': 'Update service',
        'DELETE': 'Delete service'
    },
    # Add more endpoints...
} 