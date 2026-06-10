from typing import Optional

from pydantic import BaseModel


class JobListing(BaseModel):
    source_id: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None

    def to_json(self) -> dict:
        return self.model_dump()
