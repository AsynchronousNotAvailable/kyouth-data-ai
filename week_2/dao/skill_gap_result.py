from typing import List

from pydantic import BaseModel


class SkillGapResult(BaseModel):
    gaps: List[str]
    tokens: int = 0
    time: int = 0       # seconds
    stats: dict = {}
