import asyncio
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.apps import App
from google.adk.runners import Runner

from .config import GITHUB_TOKEN, GITHUB_MCP_URL, JULES_MCP_URL, APP_NAME, GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE
from .sessions import FirestoreSessionService
from .tools import register_jules_session, update_jules_session_status

# GitHub MCP Toolset
github_toolset = McpToolset(
    connection_params=StreamableHTTPServerParams(
        url=GITHUB_MCP_URL,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-MCP-Toolsets": "repos,pull_requests,issues",
        },
    ),
)

# Jules MCP Toolset
jules_toolset = McpToolset(
    connection_params=StreamableHTTPServerParams(
        url=JULES_MCP_URL,
    ),
)

# Root Agent
root_agent = Agent(
    model="gemini-2.0-flash",
    name="personal_github_manager",
    instruction="""You are a personal GitHub manager agent.
    Your goal is to help the user manage their repositories and perform coding tasks using Jules.

    Workflows:
    1. If the user wants to create a new repository:
       - Use 'repos.create_for_authenticated_user' to create the repo.
       - Use appropriate tools to add a README and MIT license if possible, or just inform the user if it's already done by the creation tool.
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
       - Inform the user that Jules is preparing a plan and you will notify them when it's ready.

    3. If the user approves a plan (or you are told it's approved):
       - Use Jules MCP 'approve_plan' with the session name.
       - Update the status in state using 'update_jules_session_status' to 'implementing'.

    4. If a task is completed:
       - Jules will automatically create a PR (because auto_pr=True).
       - Find the PR using GitHub MCP.
       - Use GitHub MCP 'pull_requests.merge' to merge it.
       - Inform the user.
    """,
    tools=[github_toolset, jules_toolset, register_jules_session, update_jules_session_status],
)

# Initialize Session Service
session_service = FirestoreSessionService(
    project_id=GOOGLE_CLOUD_PROJECT,
    database=FIRESTORE_DATABASE
)

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
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content
    ):
        events.append(event)
    return events
