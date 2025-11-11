from pydantic import BaseModel
from typing import Optional

from uwazi_agents.domain.PropertyType import PropertyType


class TemplateProperty(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    type: PropertyType
    noLabel: Optional[bool] = False
    required: Optional[bool] = False
    showInCard: Optional[bool] = False
    filter: Optional[bool] = False
    defaultfilter: Optional[bool] = False
    prioritySorting: Optional[bool] = False
    style: Optional[str] = ""
    generatedId: Optional[bool] = False
    isCommonProperty: Optional[bool] = False

