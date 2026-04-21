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
    label: str
    key_preview: str
    created_at: str
    disabled: bool
    last_used_at: str | None


@dataclass
class CreateApiKeyRequest:
    label: str


@dataclass
class CreateApiKeyResponse:
    key_id: str
    label: str
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
            "label": r.label,
            "key_preview": _mask(r.key),
            "created_at": r.created_at,
            "disabled": r.disabled,
            "last_used_at": r.last_used_at,
        }
        for r in repo.list()
    ]


@router.post("/keys", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_key(request: Request, body: dict) -> dict:
    label = str(body.get("label") or body.get("name", "")).strip()
    if not label:
        raise HTTPException(status_code=400, detail="label is required")
    repo = _get_repo(request)
    record: ApiKeyRecord = repo.create(label)
    return {
        "key_id": record.key_id,
        "label": record.label,
        "key": record.key,
        "created_at": record.created_at,
        "disabled": record.disabled,
        "last_used_at": record.last_used_at,
    }


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_key(key_id: str, request: Request) -> None:
    repo = _get_repo(request)
    if not repo.delete(key_id):
        raise HTTPException(status_code=404, detail="API key not found")


@router.patch("/keys/{key_id}", response_model=dict)
def update_key(key_id: str, request: Request, body: dict) -> dict:
    if "disabled" not in body:
        raise HTTPException(status_code=400, detail="disabled is required")
    disabled = bool(body["disabled"])
    repo = _get_repo(request)
    if not repo.set_disabled(key_id, disabled):
        raise HTTPException(status_code=404, detail="API key not found")
    record = next((item for item in repo.list() if item.key_id == key_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return {
        "key_id": record.key_id,
        "label": record.label,
        "key_preview": _mask(record.key),
        "created_at": record.created_at,
        "disabled": record.disabled,
        "last_used_at": record.last_used_at,
    }
