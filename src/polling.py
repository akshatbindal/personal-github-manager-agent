import asyncio
import logging
import httpx
import json
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from .config import TELEGRAM_BOT_TOKEN, GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE, APP_NAME, JULES_MCP_URL
from .sessions import FirestoreSessionService
from .main import run_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def call_jules_tool(tool_name: str, arguments: dict):
    """Calls a tool on the Jules MCP server via SSE/HTTP."""
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("GET", JULES_MCP_URL, timeout=5.0) as response:
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
                res = await client.post(post_url, json=payload)
                return res.json().get("result", {}).get("content", [{}])[0].get("text")
        except Exception as e:
            logger.error(f"Error calling Jules MCP: {e}")
            return None

async def poll_sessions():
    session_service = FirestoreSessionService(project_id=GOOGLE_CLOUD_PROJECT, database=FIRESTORE_DATABASE)
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    while True:
        try:
            response = await session_service.list_sessions(app_name=APP_NAME)
            for session_info in response.sessions:
                session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=session_info.user_id,
                    session_id=session_info.id
                )

                active_jules = session.state.get("active_jules_sessions", [])
                if not active_jules:
                    continue

                for j_sess in active_jules:
                    if j_sess["status"] == "completed":
                        continue

                    logger.info(f"Checking Jules session {j_sess['id']} for user {session.user_id}")

                    result_text = await call_jules_tool("get_session", {"session_name": j_sess["id"]})
                    if not result_text:
                        continue

                    try:
                        jules_data = json.loads(result_text)
                        new_status = jules_data.get("status")

                        if new_status == "PLAN_PROPOSED" and j_sess["status"] == "pending_plan":
                            keyboard = [
                                [InlineKeyboardButton("Approve Plan", callback_data=f"approve_{j_sess['id']}")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            await bot.send_message(
                                chat_id=session.user_id,
                                text=f"Jules has proposed a plan for {j_sess['repo']}!\n\n{j_sess['id']}",
                                reply_markup=reply_markup
                            )
                            j_sess["status"] = "awaiting_approval"
                            await run_agent(session.user_id, session.id, f"Jules session {j_sess['id']} is ready for approval.")

                        elif new_status == "COMPLETED" and j_sess["status"] != "completed":
                            await bot.send_message(
                                chat_id=session.user_id,
                                text=f"Jules has completed the task for {j_sess['repo']}! Merging PR..."
                            )
                            j_sess["status"] = "completed"
                            await run_agent(session.user_id, session.id, f"Jules session {j_sess['id']} is completed.")

                    except Exception as e:
                        logger.error(f"Error parsing Jules response: {e}")

        except Exception as e:
            logger.error(f"Polling error: {e}")

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(poll_sessions())
