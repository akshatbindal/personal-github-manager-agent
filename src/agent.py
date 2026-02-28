import os
import logging
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from .tools import track_jules_session
from .config import GITHUB_TOKEN, GITHUB_MCP_URL, JULES_MCP_URL

logger = logging.getLogger(__name__)

tools = [track_jules_session]

if GITHUB_TOKEN and GITHUB_MCP_URL:
    tools.append(
        McpToolset(
            connection_params=StreamableHTTPServerParams(
                url=GITHUB_MCP_URL,
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "X-MCP-Toolsets": "all",
                    "X-MCP-Readonly": "false"
                },
            ),
        )
    )

if JULES_MCP_URL:
    tools.append(
        McpToolset(
            connection_params=StreamableHTTPServerParams(
                url=JULES_MCP_URL,
            ),
        )
    )

root_agent = Agent(
    model="gemini-2.5-flash",
    name="personal_github_manager",
    instruction="""You are a powerful AI orchestration agent capable of creating, reading, and managing GitHub repositories, and delegating complex code-writing tasks to Jules.

Here is your typical asynchronous workflow when the user asks you to build an app or write code:
1. Create a GitHub repository using your GitHub tools. IMPORTANT: You MUST initialize the repository with an initial commit (e.g., a README.md file) using your tools. Jules will fail to branch off `main` if the repository is completely empty.
2. Find the Jules source name for the repo using `list_sources`.
3. Call `create_session` using the Jules prompt, the source name, and ALWAYS set `require_plan_approval=True`.
4. Call your custom `track_jules_session` tool with `session_name`="sessions/[ID]" and `status`="polling" to inform the backend scheduler to start watching this session.
5. Inform the human user that Jules is working on the plan and that they will be notified when it is ready. DO NOT wait or loop. Say goodbye and terminate your response.

LATER, When the user (or system) messages you saying that a session is "AWAITING_APPROVAL":
1. Use `get_session_plan` to retrieve the plan.
2. Present the plan to the human user using your chat interface and explicitly ask for their approval.
3. Call `track_jules_session` with `status="awaiting_user"` so the scheduler stops polling for now.

When the human user says "I approve the plan":
1. Call `approve_plan` (or approve_session_plan) for the session.
2. Call `track_jules_session` with `status="polling"` again.
3. Inform the user you have approved it and will let them know when the PR is ready. Terminate your response.

LATER, When the system messages you saying a session has "SUCCEEDED" or generated a PR:
1. Use `get_session` to get the PR link.
2. Use your GitHub tools to merge the PR.
3. Inform the user.
4. Call `track_jules_session` with `status="completed"`.

If the system says the session "FAILED":
1. Call `list_session_activities` to read the logs.
2. Tell the user why it failed.
3. Call `track_jules_session` with `status="completed"`.
""",
    tools=tools,
)
