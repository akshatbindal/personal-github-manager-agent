from google.adk.agents.callback_context import CallbackContext

def track_jules_session(context: CallbackContext, session_name: str, status: str):
    """
    Registers or updates an active Jules session in the ADK agent state.
    This allows the background polling service to track long-running sessions.
    
    Args:
        session_name: The resource name of the session (e.g. sessions/123456)
        status: The local tracking status (e.g. "polling", "awaiting_user", "completed")
    """
    active_sessions = context.state.get("active_jules_sessions", {})
    
    # Migration handling from old array format to dict format
    if isinstance(active_sessions, list):
        new_active = {}
        for s in active_sessions:
            if "id" in s and "status" in s:
                new_active[s["id"]] = s["status"]
        active_sessions = new_active

    active_sessions[session_name] = status
    context.state["active_jules_sessions"] = active_sessions
    return f"Successfully tracked session {session_name} with status '{status}'."
