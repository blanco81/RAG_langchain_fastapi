from datetime import datetime
from typing import List
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

class DocumentBase(BaseModel):
    filename: str
    vector_data: str
    user_id: str

class DocumentCreate(DocumentBase):   
    pass

class DocumentResponse(BaseModel):
    id: str
    filename: str
    user_id: str
    upload_date: datetime
    deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class HistoryBase(BaseModel):
    query_text: str
    response_text: str
    user_id: str

class HistoryCreate(HistoryBase):   
    pass

class HistoryResponse(HistoryBase):
    id: str
    deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
