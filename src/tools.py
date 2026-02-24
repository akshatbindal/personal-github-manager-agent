from google.adk.agents.callback_context import CallbackContext

def register_jules_session(context: CallbackContext, jules_session_id: str, repo_name: str):
    """Registers an active Jules session in the agent state for monitoring."""
    active_sessions = context.state.get("active_jules_sessions", [])
    active_sessions.append({
        "id": jules_session_id,
        "repo": repo_name,
        "status": "pending_plan"
    })
    context.state["active_jules_sessions"] = active_sessions
    return f"Registered Jules session {jules_session_id} for monitoring."

def update_jules_session_status(context: CallbackContext, jules_session_id: str, status: str):
    """Updates the status of a registered Jules session."""
    active_sessions = context.state.get("active_jules_sessions", [])
    for s in active_sessions:
        if s["id"] == jules_session_id:
            s["status"] = status
    context.state["active_jules_sessions"] = active_sessions
    return f"Updated status for {jules_session_id} to {status}."
