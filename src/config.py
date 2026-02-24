import os
import logging
from dotenv import load_dotenv
from google.cloud import secretmanager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

def get_secret(secret_id, default=None):
    # 1. Try environment variable first
    val = os.getenv(secret_id)
    if val:
        logger.info(f"Found {secret_id} in environment variables.")
        return val

    # 2. Try Secret Manager if GOOGLE_CLOUD_PROJECT is set
    if GOOGLE_CLOUD_PROJECT:
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{GOOGLE_CLOUD_PROJECT}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            logger.info(f"Found {secret_id} in Secret Manager.")
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Could not fetch {secret_id} from Secret Manager: {e}")
            pass
    else:
        logger.warning(f"GOOGLE_CLOUD_PROJECT not set, skipping Secret Manager for {secret_id}")

    return default

# GitHub Configuration
GITHUB_TOKEN = get_secret("GITHUB_TOKEN")
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/")

# Jules MCP Configuration
JULES_MCP_URL = get_secret("JULES_MCP_URL")

# Telegram Configuration
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")

# Firestore Configuration
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "(default)")

# App Settings
APP_NAME = "personal-github-manager"

# Log missing critical config
if not GITHUB_TOKEN:
    logger.error("GITHUB_TOKEN is missing! GitHub tools will fail.")
if not JULES_MCP_URL:
    logger.error("JULES_MCP_URL is missing! Jules tools will fail.")
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is missing! Bot will not start.")
