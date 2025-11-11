from pydantic import BaseModel
from typing import Optional

from uwazi_agents.domain.TemplateProperty import TemplateProperty


class Template(BaseModel):
    id: Optional[str] = None
    name: str
    color: Optional[str] = "#000000"
    entityViewPage: Optional[str] = ""
    properties: list[TemplateProperty]
    commonProperties: Optional[list[TemplateProperty]] = None

