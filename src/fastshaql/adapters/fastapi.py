"""FastAPI adapter — hand-rolled graphql-core HTTP glue."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from graphql import GraphQLSchema

from fastshaql.adapters.graphiql import GRAPHIQL_HTML
from fastshaql.core import ResolverContext, execute_graphql_http

ContextGetter = (
    Callable[..., ResolverContext] | Callable[..., Awaitable[ResolverContext]]
)


def build_graphql_router(
    schema: GraphQLSchema,
    context_getter: ContextGetter,
    *,
    ide: bool = True,
    path: str = "/graphql",
) -> APIRouter:
    """Mount GraphQL POST execution and optional GraphiQL on a FastAPI router.

    Args:
        schema: Executable graphql-core schema from ``build_executable_schema``.
        context_getter: Per-request dependency returning ``ResolverContext``.
            The adapter never constructs the store — callers supply it here.
        ide: When true, GET ``path`` serves GraphiQL.
        path: URL path for both POST and GET handlers.

    Returns:
        An ``APIRouter`` to include on a FastAPI app.
    """
    router = APIRouter()

    @router.post(path)
    async def graphql_post(
        request: Request,
        resolver_ctx: Annotated[ResolverContext, Depends(context_getter)],
    ) -> Response:
        status_code, body = await execute_graphql_http(
            schema,
            content_type=request.headers.get("content-type", ""),
            body=await request.body(),
            context_value=resolver_ctx,
        )
        return Response(
            content=body,
            status_code=status_code,
            media_type="application/json",
        )

    if ide:

        @router.get(path)
        async def graphql_ide() -> HTMLResponse:
            return HTMLResponse(content=GRAPHIQL_HTML)

    return router
