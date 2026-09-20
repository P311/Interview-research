"""extract()'s JSON-repair retry is the one piece of custom protocol logic in the LLM
layer - worth exercising directly since cheap models are the reason it exists."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from jobagent.llm import extract


class Dummy(BaseModel):
    x: int


def _response(content):
    message = MagicMock(content=content)
    return MagicMock(choices=[MagicMock(message=message)])


def test_extract_succeeds_on_first_valid_response():
    with patch("jobagent.llm.LLM_API_KEY", "fake-key"), patch(
        "jobagent.llm.client.chat.completions.create", return_value=_response('{"x": 5}')
    ) as mock_create:
        result = extract(system="s", user="u", schema=Dummy)
        assert result.x == 5
        assert mock_create.call_count == 1


def test_extract_repairs_invalid_json_once():
    with patch("jobagent.llm.LLM_API_KEY", "fake-key"), patch(
        "jobagent.llm.client.chat.completions.create",
        side_effect=[_response("not json at all"), _response('{"x": 7}')],
    ) as mock_create:
        result = extract(system="s", user="u", schema=Dummy)
        assert result.x == 7
        assert mock_create.call_count == 2


def test_extract_gives_up_after_one_repair_attempt():
    with patch("jobagent.llm.LLM_API_KEY", "fake-key"), patch(
        "jobagent.llm.client.chat.completions.create",
        side_effect=[_response("not json"), _response("still not json")],
    ) as mock_create:
        with pytest.raises(Exception):
            extract(system="s", user="u", schema=Dummy)
        assert mock_create.call_count == 2


def test_extract_requires_an_api_key():
    with patch("jobagent.llm.LLM_API_KEY", ""):
        with pytest.raises(RuntimeError):
            extract(system="s", user="u", schema=Dummy)
