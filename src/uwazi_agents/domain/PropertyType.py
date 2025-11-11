from enum import StrEnum


class PropertyType(StrEnum):
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

