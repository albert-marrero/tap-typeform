"""Typeform tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_typeform.streams import (
    TypeformStream,
    FormsStream,
    QuestionsStream,
    AnswersStream
)

STREAM_TYPES = [
    FormsStream,
    QuestionsStream,
    AnswersStream
]


class TapTypeform(Tap):
    """Typeform tap class."""
    name = "tap-typeform"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "personal_access_token",
            th.StringType,
            required=True,
            description="Your personal access token for Typeform's API."
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]
