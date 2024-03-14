"""Stream type classes for tap-typeform."""
import json
import requests
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_typeform.client import TypeformStream

class FormsStream(TypeformStream):
    """Define custom stream."""
    name = "forms"
    path = "/forms"
    primary_keys = ["id"]
    replication_key = None
    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("title", th.StringType),
        th.Property("link", th.StringType),
        th.Property("last_updated_at", th.StringType),
        th.Property("created_at", th.StringType),
    ).to_dict()

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        data = response.json()
        forms = data.get("items")

        if forms_ids := self.config.get("forms_ids_list"):
            forms_ids = forms_ids.split(',')
            forms = [form for form in forms if form['id'] in forms_ids ]

        for form in forms:
            yield {
                "id": form.get("id"),
                "title": form.get("title"),
                "link": form.get("_links").get("display"),
                "last_updated_at": form.get("last_updated_at"),
                "created_at": form.get("created_at"),
            }

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        previous_token = previous_token or 1

        data = response.json()

        page_count = data["page_count"]

        if page_count < previous_token:
            return None

        return previous_token + 1

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        return {
            "form_id": record["id"],
        }

class QuestionsStream(TypeformStream):
    """Define custom stream."""
    name = "questions"
    parent_stream_type = FormsStream
    path = "/forms/{form_id}"
    primary_keys = ["id"]
    replication_key = None
    schema = th.PropertiesList(
        th.Property("form_id", th.StringType),
        th.Property("id", th.StringType),
        th.Property("title", th.StringType),
        th.Property("type", th.StringType),
    ).to_dict()

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        data = response.json()
        fields = data.get("fields")

        for question in fields:
            yield {
                "form_id": data.get("id"),
                "id": question.get("id"),
                "title": question.get("title"),
                "type": question.get("type")
            }

class AnswersStream(TypeformStream):
    """Define custom stream."""
    name = "answers"
    parent_stream_type = FormsStream
    path = "/forms/{form_id}/responses"
    primary_keys = ["form_id", "question_id", "response_id"]
    replication_key = "submitted_at"
    schema = th.PropertiesList(
        th.Property("form_id", th.StringType),
        th.Property("response_id", th.StringType),
        th.Property("question_id", th.StringType),
        th.Property("data_type", th.StringType),
        th.Property("answer", th.StringType),
        th.Property("submitted_at", th.DateTimeType),
        th.Property("landed_at", th.DateTimeType),
        th.Property("browser", th.StringType),
        th.Property("network_id", th.StringType),
        th.Property("referer", th.StringType),
        th.Property("user_agent", th.StringType),
        th.Property("token", th.StringType),
        th.Property("user_id", th.StringType),
        th.Property("nps_scores_id", th.StringType),
    ).to_dict()

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        row["form_id"] = context["form_id"]
        return row

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        data = response.json()
        items = data.get("items")

        if items:
            for item in items:
                answers = item.get("answers")

                if answers:
                    for answer in answers:
                        data_type = answer.get('type')

                        if data_type in ['choice', 'choices', 'payment']:
                            answer_value = json.dumps(answer.get(data_type))
                        elif data_type in ['number', 'boolean']:
                            answer_value = str(answer.get(data_type))
                        else:
                            answer_value = answer.get(data_type)
                        user_id = item.get('hidden', {}).get('user_id')
                        nps_scores_id = item.get('hidden', {}).get('nps_scores_id')

                        yield {
                            "question_id": answer.get('field').get('id'),
                            "data_type": data_type,
                            "answer": answer_value,
                            "response_id": item['response_id'],
                            "submitted_at": item['submitted_at'],
                            "landed_at": item['landed_at'],
                            "browser": item['metadata']['browser'],
                            "network_id": item['metadata']['network_id'],
                            "referer": item['metadata']['referer'],
                            "user_agent": item['metadata']['user_agent'],
                            "token": item['token'],
                            "user_id": user_id,
                            "nps_scores_id": nps_scores_id,
                        }

        return None


    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {
            "page_size": 1000
        }
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            params["sort"] = f"{self.replication_key},asc"
            params["since"] = self.get_starting_replication_key_value(context)
        return params
