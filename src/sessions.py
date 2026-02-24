import uuid
import time
from typing import Any, Optional, List
from google.cloud import firestore
from google.adk.sessions.base_session_service import BaseSessionService, GetSessionConfig, ListSessionsResponse
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.sessions.state import State

class FirestoreSessionService(BaseSessionService):
    def __init__(self, project_id: str, database: str = "(default)"):
        self.db = firestore.AsyncClient(project=project_id, database=database)
        self.sessions_col = self.db.collection("adk_sessions")

    def _get_session_ref(self, app_name: str, user_id: str, session_id: str):
        # Using a composite key for document ID
        doc_id = f"{app_name}:{user_id}:{session_id}"
        return self.sessions_col.document(doc_id)

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        if not session_id:
            session_id = str(uuid.uuid4())

        state = state or {}
        now = time.time()

        session_ref = self._get_session_ref(app_name, user_id, session_id)
        await session_ref.set({
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "state": state,
            "last_update_time": now,
            "created_at": now
        })

        return Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state,
            last_update_time=now
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        session_ref = self._get_session_ref(app_name, user_id, session_id)
        doc = await session_ref.get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=data.get("state", {}),
            last_update_time=data.get("last_update_time", time.time())
        )

        # Load events
        events_ref = session_ref.collection("events").order_by("timestamp")
        if config and config.after_timestamp:
            events_ref = events_ref.where("timestamp", ">=", config.after_timestamp)

        # We don't have a limit easily here if we want "most recent",
        # but for simplicity we'll just fetch all or some.
        # ADK events are often replayed.

        async for event_doc in events_ref.stream():
            event_data = event_doc.to_dict()
            # Note: You might need to deserialize complex types in event_data
            # For this MVP, we assume they are serializable or handled by ADK
            # In a real implementation, we'd use Event.model_validate
            session.events.append(Event(**event_data))

        if config and config.num_recent_events:
            session.events = session.events[-config.num_recent_events:]

        return session

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        query = self.sessions_col.where("app_name", "==", app_name)
        if user_id:
            query = query.where("user_id", "==", user_id)

        sessions = []
        async for doc in query.stream():
            data = doc.to_dict()
            sessions.append(Session(
                app_name=app_name,
                user_id=data["user_id"],
                id=data["session_id"],
                state=data.get("state", {}),
                last_update_time=data.get("last_update_time", time.time())
            ))
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        session_ref = self._get_session_ref(app_name, user_id, session_id)
        # Delete sub-collections (Firestore doesn't do this automatically)
        events_ref = session_ref.collection("events")
        async for doc in events_ref.stream():
            await doc.reference.delete()
        await session_ref.delete()

    async def append_event(self, session: Session, event: Event) -> Event:
        # Standard updates
        event = await super().append_event(session, event)

        session_ref = self._get_session_ref(session.app_name, session.user_id, session.id)

        # Update session state and timestamp
        await session_ref.update({
            "state": session.state,
            "last_update_time": event.timestamp
        })

        # Store event
        event_dict = event.model_dump(exclude_none=True)
        await session_ref.collection("events").add(event_dict)

        return event
