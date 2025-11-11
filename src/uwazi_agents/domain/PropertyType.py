from enum import Enum


class PropertyType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    NUMERIC = "numeric"
    DATE = "date"
    LINK = "link"
    SELECT = "select"
    MULTISELECT = "multiselect"
    RELATIONSHIP = "relationship"
    NESTED = "nested"
    IMAGE = "image"
    MEDIA = "media"
    PREVIEW = "preview"
    GEOLOCATION = "geolocation"

