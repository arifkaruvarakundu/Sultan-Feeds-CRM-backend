from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Optional

class WhatsAppTemplateBase(BaseModel):
    template_name: str
    category: str | None = None
    language: str
    status: str
    body: str | None = None
    updated_at: datetime

    class Config:
        orm_mode = True

class SendMessageRequest(BaseModel):
    customers: List[int]
    templates: List[str]
    variables: Optional[Dict[int, List[str]]] = None 