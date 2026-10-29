from datetime import datetime
from pydantic import BaseModel, Field


class EnvVarInput(BaseModel):
    key: str = Field(..., pattern=r"^[A-Z_][A-Z0-9_]*$", description="Kalit formati [A-Z_][A-Z0-9_]* bo'lishi shart.")
    value: str = Field(..., min_length=1)


class EnvVarOut(BaseModel):
    id: str
    key: str
    masked_value: str

    class Config:
        from_attributes = True


class BotOut(BaseModel):
    id: str
    user_id: str
    name: str
    entrypoint: str
    has_requirements: bool
    status: str
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BotDetail(BotOut):
    env_vars: list[EnvVarOut] = []


class EnvVarsUpdate(BaseModel):
    env_vars: list[EnvVarInput]
