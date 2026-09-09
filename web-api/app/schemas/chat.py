from pydantic import BaseModel


class QaBody(BaseModel):
    question: str
