import os
from dotenv import load_dotenv
from aztp_client import Aztp
import logging

logger = logging.getLogger(__name__)

_aztp_client_instance = None

def get_aztp_client():
    global _aztp_client_instance
    if _aztp_client_instance is None:
        load_dotenv()  # Load environment variables from .env
        api_key = os.getenv("AZTP_API_KEY")
        if not api_key:
            logger.warning("AZTP_API_KEY not found in environment variables. AZTP client will not be initialized.")
            # Optionally, you could raise an error here if AZTP is strictly required:
            # raise ValueError("AZTP_API_KEY is essential for AZTP client initialization.")
            return None  # Or handle as appropriate for your application's needs

        try:
            _aztp_client_instance = Aztp(api_key=api_key)
            logger.info("AZTP client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize AZTP client: {e}")
            # Depending on the severity, you might want to raise the error or return None
            return None
    return _aztp_client_instance

# Example of how to potentially use it (optional, for direct testing of this file)
# if __name__ == '__main__':
#     client = get_aztp_client()
#     if client:
#         print("AZTP Client obtained successfully.")
#     else:
#         print("Failed to obtain AZTP Client.")
