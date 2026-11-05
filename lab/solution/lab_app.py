from dataclasses import dataclass
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, model_validator,
)


app = FastAPI(title="FastAPI Event Lab")


class EventIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    start_time: AwareDatetime
    end_time: AwareDatetime
    capacity: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class EventOut(EventIn):
    id: str


@dataclass(frozen=True)
class CapacityPolicy:
    max_capacity: int = 50


def get_policy() -> CapacityPolicy:
    return CapacityPolicy()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/events", response_model=EventOut, status_code=201)
def create_event(
    payload: EventIn,
    policy: CapacityPolicy = Depends(get_policy),
):
    if payload.capacity > policy.max_capacity:
        raise HTTPException(
            status_code=400, detail="CAPACITY_POLICY_LIMIT",
        )
    return {
        "id": str(uuid4()),
        **payload.model_dump(),
        "internal_note": "classroom-only",
    }


# Bài mở rộng (mục 8 tài liệu lab): chờ hợp tác với async
import asyncio  # noqa: E402


@app.get("/wait")
async def wait_for_io():
    await asyncio.sleep(3)
    return {"done": True}
