import os
from dotenv import load_dotenv
from google.cloud import secretmanager

load_dotenv()

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

def get_secret(secret_id, default=None):
    # 1. Try environment variable first
    val = os.getenv(secret_id)
    if val:
        return val

    # 2. Try Secret Manager if GOOGLE_CLOUD_PROJECT is set
    if GOOGLE_CLOUD_PROJECT:
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{GOOGLE_CLOUD_PROJECT}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception:
            # Silently fail and fallback to default if secret is not found or no access
            pass

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
