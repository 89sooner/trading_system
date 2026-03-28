from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request, status

from trading_system.api.admin.repository import ApiKeyRecord, ApiKeyRepository

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _get_repo(request: Request) -> ApiKeyRepository:
    return request.app.state.api_key_repository


@dataclass
class ApiKeyListItem:
    key_id: str
    name: str
    key_preview: str
    created_at: str


@dataclass
class CreateApiKeyRequest:
    name: str


@dataclass
class CreateApiKeyResponse:
    key_id: str
    name: str
    key: str
    created_at: str


def _mask(key: str) -> str:
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}" if len(key) > 8 else "****"


@router.get("/keys", response_model=list[dict])
def list_keys(request: Request) -> list[dict]:
    repo = _get_repo(request)
    return [
        {
            "key_id": r.key_id,
            "name": r.name,
            "key_preview": _mask(r.key),
            "created_at": r.created_at,
        }
        for r in repo.list()
    ]


@router.post("/keys", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_key(request: Request, body: dict) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    repo = _get_repo(request)
    record: ApiKeyRecord = repo.create(name)
    return {
        "key_id": record.key_id,
        "name": record.name,
        "key": record.key,
        "created_at": record.created_at,
    }


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_key(key_id: str, request: Request) -> None:
    repo = _get_repo(request)
    if not repo.delete(key_id):
        raise HTTPException(status_code=404, detail="API key not found")
