import os
import logging
from bot import main

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create required directories
directories = ['data', 'backups', 'logs', 'temp', 'cache']
for directory in directories:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Created directory: {directory}")

if __name__ == '__main__':
    main() 