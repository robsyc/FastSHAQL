"""GraphQL-over-HTTP envelope — request validation, execution, response bytes.

Framework-neutral (ADR-0001): the FastAPI and Django adapters extract raw body
bytes, Content-Type, and the resolved request context from their request
objects and delegate the ADR-0019 HTTP contract here — validation, graphql-core
execution, and serialization — so both adapters share one implementation
rather than mirroring duplicated orchestration. JSON is encoded and decoded
with orjson.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import orjson
from graphql import GraphQLSchema, graphql


@dataclass(frozen=True)
class GraphqlHttpRequest:
    """A validated GraphQL-over-HTTP POST body (ADR-0019)."""

    query: str
    variables: dict[str, Any] | None
    operation_name: str | None


@dataclass(frozen=True)
class RequestError:
    """A pre-execution validation failure carrying an HTTP status and message."""

    status_code: int
    message: str


def parse_graphql_http_request(
    *, content_type: str, body: bytes
) -> GraphqlHttpRequest | RequestError:
    """Validate a GraphQL-over-HTTP request per ADR-0019.

    The contract: POST with a ``application/json`` Content-Type (this also
    doubles as a CSRF mitigation) and a JSON object body carrying ``query``
    (required string), ``variables`` (optional object), and ``operationName``
    (optional string). Validation is fail-fast — the first failing check wins.

    Args:
        content_type: The raw ``Content-Type`` header value.
        body: The raw request body bytes.

    Returns:
        :class:`GraphqlHttpRequest` on success, or :class:`RequestError`
        (status 415 or 400) on the first validation failure.
    """
    if not content_type.startswith("application/json"):
        return RequestError(415, "Unsupported Content-Type")
    try:
        parsed: Any = orjson.loads(body)
    except orjson.JSONDecodeError:
        return RequestError(400, "Invalid JSON")
    if not isinstance(parsed, dict):
        return RequestError(400, "Request body must be a JSON object")

    query = parsed.get("query")
    if not isinstance(query, str):
        return RequestError(400, "Missing or invalid query")

    variables = parsed.get("variables")
    if variables is not None and not isinstance(variables, dict):
        return RequestError(400, "Invalid variables")

    operation_name = parsed.get("operationName")
    if operation_name is not None and not isinstance(operation_name, str):
        return RequestError(400, "Invalid operationName")

    return GraphqlHttpRequest(
        query=query, variables=variables, operation_name=operation_name
    )


def graphql_error_payload(message: str) -> dict[str, Any]:
    """Build the GraphQL error response body for a single message."""
    return {"errors": [{"message": message}]}


def dump_graphql_json(payload: object) -> bytes:
    """Serialize a graphql-core formatted result or error payload to JSON bytes.

    Returns UTF-8 bytes; no ``charset`` is needed on ``Content-Type`` since JSON
    is UTF-8 by default (RFC 8259). This is the single orjson serialization seam
    for adapter responses.
    """
    return orjson.dumps(payload)


async def execute_graphql_http(
    schema: GraphQLSchema,
    *,
    content_type: str,
    body: bytes,
    context_value: Any,
) -> tuple[int, bytes]:
    """Validate and execute one GraphQL-over-HTTP operation (ADR-0019).

    The full adapter contract in one call: envelope validation, graphql-core
    execution, and response serialization. Returns ``(status_code, body)``
    with UTF-8 JSON bytes — the ``{data, errors}`` payload at 200 for an
    executed operation, or the error payload at its :class:`RequestError`
    status (415/400) for a request that never reached execution. Adapters
    wrap the pair in their framework's response type.
    """
    parsed = parse_graphql_http_request(content_type=content_type, body=body)
    if isinstance(parsed, RequestError):
        return (
            parsed.status_code,
            dump_graphql_json(graphql_error_payload(parsed.message)),
        )
    result = await graphql(
        schema,
        parsed.query,
        variable_values=parsed.variables,
        operation_name=parsed.operation_name,
        context_value=context_value,
    )
    return 200, dump_graphql_json(result.formatted)
