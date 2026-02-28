import os
import logging
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from google.adk.runners import Runner
from google.genai import types

from .agent import root_agent
from .config import GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE, APP_NAME, JULES_MCP_URL
from .sessions import FirestoreSessionService
from .telegram import send_telegram_message

import httpx

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Personal GitHub Manager Agent")

# Initialize Session Service
if GOOGLE_CLOUD_PROJECT:
    session_service = FirestoreSessionService(
        project_id=GOOGLE_CLOUD_PROJECT,
        database=FIRESTORE_DATABASE
    )
    logger.info("Firestore Session Service initialized.")
else:
    from google.adk.sessions import InMemorySessionService
    session_service = InMemorySessionService()
    logger.warning("GOOGLE_CLOUD_PROJECT not set, using InMemorySessionService.")

# Initialize Runner
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

async def run_agent_and_reply(user_id: str, session_id: str, message: str):
    """Runs the agent with the given message and sends the response back to Telegram."""
    content = types.Content(role="user", parts=[types.Part(text=message)])
    
    response_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            if event.author == "personal_github_manager" and event.content:
                if hasattr(event.content, "parts"):
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
        
        if response_text:
           await send_telegram_message(chat_id=user_id, text=response_text)
    except Exception as e:
        logger.error(f"Error running agent: {e}")
        await send_telegram_message(chat_id=user_id, text=f"I encountered an error: {e}")

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook endpoint for Telegram bot updates."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle standard messages
    if "message" in data and "text" in data["message"]:
        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"]["text"]
        
        # We process the agent call in the background to avoid Telegram webhook timeouts
        background_tasks.add_task(run_agent_and_reply, user_id=chat_id, session_id="default_jules_session", message=text)
        return {"status": "ok"}
        
    return {"status": "ignored"}


# --- JULES POLLING LOGIC ---

async def call_jules_tool(tool_name: str, arguments: dict):
    """Calls a tool on the remote Jules MCP server via SSE/HTTP."""
    if not JULES_MCP_URL:
        return None
        
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("GET", JULES_MCP_URL, timeout=10.0) as response:
                post_url = None
                async for line in response.aiter_lines():
                    if line.startswith("event: endpoint"):
                        continue
                    if line.startswith("data: "):
                        post_url = line.replace("data: ", "").strip()
                        if not post_url.startswith("http"):
                            base_url = str(response.url).rsplit('/', 1)[0]
                            post_url = f"{base_url}/{post_url.lstrip('/')}"
                        break

                if not post_url:
                    logger.error("Could not find POST endpoint from SSE")
                    return None

                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                }
                res = await client.post(post_url, json=payload, timeout=30.0)
                return res.json().get("result", {}).get("content", [{}])[0].get("text")
        except Exception as e:
            logger.error(f"Error calling Jules MCP: {e}")
            return None


@app.get("/scheduler/poll-jules")
async def poll_jules(background_tasks: BackgroundTasks):
    """Endpoint triggered by Cloud Scheduler every 1 minute."""
    try:
        res = await session_service.list_sessions(app_name=APP_NAME)
        # Note: res is a ListSessionsResponse with a .sessions list of Session configs
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return {"status": "error"}

    for session_info in res.sessions:
        try:
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=session_info.user_id,
                session_id=session_info.id
            )
            
            active_jules = session.state.get("active_jules_sessions", {})
            if not isinstance(active_jules, dict):
                continue

            for jules_session_name, tracking_status in active_jules.items():
                if tracking_status == "polling":
                    background_tasks.add_task(
                        check_jules_and_notify, 
                        session.user_id, 
                        session.id, 
                        jules_session_name
                    )
        except Exception as e:
            logger.error(f"Failed to process session {session_info.id}: {e}")

    return {"status": "polling_jobs_queued"}

async def check_jules_and_notify(user_id: str, session_id: str, jules_session_name: str):
    """Checks the status from Jules and wakes up the LLM if intervention is needed."""
    logger.info(f"Checking Jules session: {jules_session_name}")
    result_text = await call_jules_tool("get_session", {"session_name": jules_session_name})
    
    if not result_text:
        return
        
    system_prompt = None
    
    if "State: AWAITING_APPROVAL" in result_text:
        system_prompt = f"[SYSTEM NOTIFICATION] Jules session {jules_session_name} is AWAITING_APPROVAL. Please use get_session_plan, retrieve the plan, and ask the user for approval immediately."
    elif "State: SUCCEEDED" in result_text or "Pull Request created" in result_text:
        system_prompt = f"[SYSTEM NOTIFICATION] Jules session {jules_session_name} SUCCEEDED. Please check if a PR was generated, merge it using your GitHub tools, and notify the user."
    elif "State: FAILED" in result_text or "State: CANCELLED" in result_text:
        system_prompt = f"[SYSTEM NOTIFICATION] Jules session {jules_session_name} FAILED or was CANCELLED. Please use list_session_activities to determine why and notify the user."

    if system_prompt:
        logger.info(f"Jules event detected! Waking agent with prompt: {system_prompt}")
        await run_agent_and_reply(user_id, session_id, system_prompt)

