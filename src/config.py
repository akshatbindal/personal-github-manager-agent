import os
from dotenv import load_dotenv

load_dotenv()

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"

# Jules MCP Configuration
JULES_MCP_URL = os.getenv("JULES_MCP_URL")

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# GCP Configuration
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "(default)")

# App Settings
APP_NAME = "personal-github-manager"
