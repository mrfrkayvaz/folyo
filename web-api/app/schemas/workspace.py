from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str | None = None


class WorkspaceItem(BaseModel):
    id: str
    name: str
    created_at: str
    last_message_at: str | None = None


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceItem]
