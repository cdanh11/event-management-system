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
    capacity: int  # TODO A: rang buoc so nguyen duong

    @model_validator(mode="after")
    def validate_times(self):
        # TODO B: end_time phai sau start_time
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
def create_event(payload: EventIn):
    # TODO C: nhan policy qua Depends va kiem tra gioi han
    return {
        "id": str(uuid4()),
        **payload.model_dump(),
        "internal_note": "classroom-only",
    }
