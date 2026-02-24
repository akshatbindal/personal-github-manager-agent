import asyncio
import logging
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.apps import App
from google.adk.runners import Runner

from .config import GITHUB_TOKEN, GITHUB_MCP_URL, JULES_MCP_URL, APP_NAME, GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE
from .sessions import FirestoreSessionService
from .tools import register_jules_session, update_jules_session_status

logger = logging.getLogger(__name__)

tools = [register_jules_session, update_jules_session_status]

# GitHub MCP Toolset
if GITHUB_TOKEN and GITHUB_MCP_URL:
    try:
        github_toolset = McpToolset(
            connection_params=StreamableHTTPServerParams(
                url=GITHUB_MCP_URL,
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "X-MCP-Toolsets": "repos,pull_requests,issues",
                },
            ),
        )
        tools.append(github_toolset)
        logger.info("GitHub Toolset initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize GitHub Toolset: {e}")
else:
    logger.warning("GitHub Configuration missing, GitHub tools will not be available.")

# Jules MCP Toolset
if JULES_MCP_URL:
    try:
        jules_toolset = McpToolset(
            connection_params=StreamableHTTPServerParams(
                url=JULES_MCP_URL,
            ),
        )
        tools.append(jules_toolset)
        logger.info("Jules Toolset initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Jules Toolset: {e}")
else:
    logger.warning("Jules MCP URL missing, Jules tools will not be available.")

# Root Agent
root_agent = Agent(
    model="gemini-2.0-flash",
    name="personal_github_manager",
    instruction="""You are a personal GitHub manager agent.
    Your goal is to help the user manage their repositories and perform coding tasks using Jules.

    Workflows:
    1. If the user wants to create a new repository:
       - Use 'repos.create_for_authenticated_user' to create the repo.
       - Use appropriate tools to add a README and MIT license if possible.
       - Inform the user once done.

    2. If the user wants to perform a coding task:
       - Identify the repository (e.g., owner/repo).
       - Use Jules MCP 'list_sources' and 'get_source' to find the source.
       - Create a Jules session using 'create_session' with:
         - source: the source resource name (e.g., sources/github/owner/repo)
         - instruction: the task
         - require_plan_approval: True
         - auto_pr: True
       - Use 'register_jules_session' to store the session ID and repo name in your state.
       - Inform the user that Jules is preparing a plan.

    3. If the user approves a plan:
       - Use Jules MCP 'approve_plan' with the session name.
       - Update the status in state using 'update_jules_session_status' to 'implementing'.

    4. If a task is completed:
       - Use GitHub MCP 'pull_requests.merge' to merge the resulting PR.
       - Inform the user.
    """,
    tools=tools,
)

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

async def run_agent(user_id: str, session_id: str, message: str):
    from google.genai import types
    content = types.Content(role="user", parts=[types.Part(text=message)])

    events = []
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            events.append(event)
    except Exception as e:
        logger.error(f"Error running agent: {e}")
        # Return a synthetic event for the bot to display the error
        from google.adk.events.event import Event
        error_event = Event(
            author="personal_github_manager",
            content=types.Content(parts=[types.Part(text=f"I encountered an error: {e}")])
        )
        events.append(error_event)

    return events
