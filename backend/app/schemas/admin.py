from pydantic import BaseModel, Field


class UserPlanUpdate(BaseModel):
    plan: str = Field(..., pattern="^(free|paid)$")


class UserBanUpdate(BaseModel):
    is_banned: bool


class SystemStatsOut(BaseModel):
    total_users: int
    total_bots: int
    running_bots: int
    stopped_bots: int
    crashed_bots: int
    total_cpu_allocated: float
    total_memory_allocated_mb: int
    free_plan_users: int
    paid_plan_users: int
