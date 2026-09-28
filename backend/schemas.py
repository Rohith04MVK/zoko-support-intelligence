"""Request contracts exposed in the local FastAPI OpenAPI documentation."""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Sender(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    customer_id: str = Field(min_length=1, max_length=200)
    agent_id: str = Field(min_length=1, max_length=200)


class SendMessage(Sender):
    message: str = Field(min_length=1, max_length=4096)

    @field_validator('message')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Message cannot be blank')
        return value


class RequestFeedback(Sender):
    conversation_id: str = Field(min_length=1, max_length=200)
