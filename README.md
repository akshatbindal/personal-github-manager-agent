# Personal GitHub Manager Agent

Autonomous Personal GitHub Manager Agent built with Google ADK, GitHub MCP, and Jules MCP.

## Features
- **GitHub Integration**: Create repos, merge PRs, list issues via GitHub MCP.
- **AI Coding**: Perform complex tasks using Jules MCP.
- **Asynchronous Workflow**: Polling service monitors long-running Jules tasks.
- **Telegram Interface**: Remote control via a Telegram bot with Human-in-the-Loop approvals.
- **Persistent State**: Custom Firestore session storage.
- **Cloud Native**: Deployable on Google Cloud Run with Secret Manager support.

## Setup Instructions

### 1. Google Cloud Setup
- Create a GCP Project.
- Enable APIs: Cloud Run, Firestore, Secret Manager, Cloud Build.
- **Create a Firestore database in Native mode**:
  ```bash
  # Replace [REGION] with your preferred region (e.g., us-central1)
  gcloud firestore databases create --location=[REGION] --type=firestore-native
  ```

### 2. Secrets Management (Recommended)
You can store your sensitive tokens in Secret Manager:
```bash
# Create secrets
echo -n "your_github_pat" | gcloud secrets create GITHUB_TOKEN --data-file=-
echo -n "your_telegram_bot_token" | gcloud secrets create TELEGRAM_BOT_TOKEN --data-file=-
echo -n "https://your-jules-mcp-url/mcp/sse" | gcloud secrets create JULES_MCP_URL --data-file=-

# Grant access to the Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in GITHUB_TOKEN TELEGRAM_BOT_TOKEN JULES_MCP_URL; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

Alternatively, you can provide them as environment variables in Cloud Run.

### 3. Deployment
```bash
# Build and Push
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/github-manager-agent

# Deploy
gcloud run deploy github-manager-agent \
  --image gcr.io/$(gcloud config get-value project)/github-manager-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project) \
  --allow-unauthenticated
```

## Usage
1. Start the bot on Telegram.
2. Send a command like: "Create a new repo 'test-repo' and add a hello world python script."
3. Wait for the plan notification.
4. Click **Approve Plan**.
5. Once Jules finishes, the agent will merge the PR and notify you.
