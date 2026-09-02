"""GraphQL-over-HTTP envelope — ``core/envelope.py``.

Unit tier: the request validation ladder (ADR-0019), error payload shape, and
the orjson response serialization seam shared by both adapters.
"""

from __future__ import annotations

import orjson
from graphql import (
    GraphQLArgument,
    GraphQLField,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
)

from fastshaql.core.kernel.envelope import (
    GraphqlHttpRequest,
    RequestError,
    dump_graphql_json,
    execute_graphql_http,
    graphql_error_payload,
    parse_graphql_http_request,
)

_JSON = "application/json"


def _request(body: bytes, content_type: str = _JSON):
    return parse_graphql_http_request(content_type=content_type, body=body)


def _body(**fields: object) -> bytes:
    return orjson.dumps(fields)


def test_valid_full_request() -> None:
    parsed = _request(_body(query="{ x }", variables={"a": 1}, operationName="Op"))
    assert parsed == GraphqlHttpRequest(
        query="{ x }", variables={"a": 1}, operation_name="Op"
    )


def test_valid_minimal_request() -> None:
    parsed = _request(_body(query="{ x }"))
    assert isinstance(parsed, GraphqlHttpRequest)
    assert parsed.query == "{ x }"
    assert parsed.variables is None
    assert parsed.operation_name is None


def test_content_type_with_charset_accepted() -> None:
    parsed = _request(
        _body(query="{ x }"), content_type="application/json; charset=utf-8"
    )
    assert isinstance(parsed, GraphqlHttpRequest)


def test_wrong_content_type_returns_415() -> None:
    parsed = _request(_body(query="{ x }"), content_type="text/plain")
    assert parsed == RequestError(415, "Unsupported Content-Type")


def test_malformed_json_returns_400() -> None:
    assert _request(b"{not json") == RequestError(400, "Invalid JSON")


def test_list_body_returns_400() -> None:
    assert _request(b"[1, 2, 3]") == RequestError(
        400, "Request body must be a JSON object"
    )


def test_scalar_body_returns_400() -> None:
    assert _request(b"123") == RequestError(400, "Request body must be a JSON object")


def test_missing_query_returns_400() -> None:
    assert _request(_body()) == RequestError(400, "Missing or invalid query")


def test_non_string_query_returns_400() -> None:
    assert _request(_body(query=123)) == RequestError(400, "Missing or invalid query")


def test_non_object_variables_returns_400() -> None:
    assert _request(_body(query="{ x }", variables="nope")) == RequestError(
        400, "Invalid variables"
    )


def test_null_variables_accepted() -> None:
    parsed = _request(_body(query="{ x }", variables=None))
    assert isinstance(parsed, GraphqlHttpRequest)
    assert parsed.variables is None


def test_non_string_operation_name_returns_400() -> None:
    assert _request(_body(query="{ x }", operationName=123)) == RequestError(
        400, "Invalid operationName"
    )


def test_null_operation_name_accepted() -> None:
    parsed = _request(_body(query="{ x }", operationName=None))
    assert isinstance(parsed, GraphqlHttpRequest)
    assert parsed.operation_name is None


def test_graphql_error_payload_shape() -> None:
    assert graphql_error_payload("boom") == {"errors": [{"message": "boom"}]}


def test_dump_graphql_json_returns_bytes_and_round_trips() -> None:
    payload = {"data": {"x": 1}, "errors": None}
    raw = dump_graphql_json(payload)
    assert isinstance(raw, bytes)
    assert orjson.loads(raw) == payload


def test_dump_graphql_json_emits_raw_utf8() -> None:
    # orjson emits raw UTF-8 rather than \uXXXX escapes.
    raw = dump_graphql_json({"data": {"label": "café"}})
    assert "café".encode() in raw


def test_error_payload_serializes_to_response_bytes() -> None:
    raw = dump_graphql_json(graphql_error_payload("nope"))
    assert orjson.loads(raw) == {"errors": [{"message": "nope"}]}


# --- execute_graphql_http (the full adapter contract) ---


def _schema() -> GraphQLSchema:
    return GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            {
                "hello": GraphQLField(
                    GraphQLString, resolve=lambda _src, _info: "world"
                ),
                "echo": GraphQLField(
                    GraphQLString,
                    args={"value": GraphQLArgument(GraphQLString)},
                    resolve=lambda _src, _info, value: value,
                ),
            },
        )
    )


async def test_execute_returns_200_with_data() -> None:
    status, body = await execute_graphql_http(
        _schema(), content_type=_JSON, body=_body(query="{ hello }"), context_value=None
    )
    assert status == 200
    assert orjson.loads(body) == {"data": {"hello": "world"}}


async def test_execute_request_error_serializes_message() -> None:
    status, body = await execute_graphql_http(
        _schema(),
        content_type="text/plain",
        body=_body(query="{ hello }"),
        context_value=None,
    )
    assert status == 415
    assert orjson.loads(body) == {"errors": [{"message": "Unsupported Content-Type"}]}


async def test_execute_threads_variables_to_the_operation() -> None:
    body = _body(
        query="query Q($v: String!) { echo(value: $v) }", variables={"v": "hi"}
    )
    status, raw = await execute_graphql_http(
        _schema(), content_type=_JSON, body=body, context_value=None
    )
    assert status == 200
    assert orjson.loads(raw) == {"data": {"echo": "hi"}}


async def test_execute_threads_operation_name_among_multiple_operations() -> None:
    body = _body(
        query='query A { hello } query B { echo(value: "chosen") }', operationName="B"
    )
    status, raw = await execute_graphql_http(
        _schema(), content_type=_JSON, body=body, context_value=None
    )
    assert status == 200
    assert orjson.loads(raw) == {"data": {"echo": "chosen"}}
