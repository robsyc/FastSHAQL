"""Django adapter — hand-rolled graphql-core HTTP glue."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from fastshaql.adapters.graphiql import GRAPHIQL_HTML
from fastshaql.core import ResolverContext, execute_graphql_http

if TYPE_CHECKING:
    from graphql import GraphQLSchema

ContextGetter = (
    Callable[[HttpRequest], ResolverContext]
    | Callable[[HttpRequest], Awaitable[ResolverContext]]
)


def build_graphql_view(
    schema: GraphQLSchema,
    get_context: ContextGetter | None = None,
    *,
    ide: bool = True,
) -> type[View]:
    """Return a CSRF-exempt async ``View`` subclass bound to ``schema``.

    Wire in ``urls.py``::

        path("graphql/", build_graphql_view(schema, get_context).as_view())

    Args:
        schema: Executable graphql-core schema from ``build_executable_schema``.
        get_context: Per-request callable ``(request) -> ResolverContext``.
            The adapter never constructs the store — callers supply it here.
            Omit to subclass and override ``get_context(self, request)``.
        ide: When true, GET serves GraphiQL.

    Returns:
        A ``View`` subclass to mount with ``.as_view()``.
    """

    def _default_get_context(_request: HttpRequest) -> ResolverContext:
        raise NotImplementedError(
            "Provide get_context to build_graphql_view or override get_context"
        )

    context_fn = get_context or _default_get_context

    @method_decorator(csrf_exempt, name="dispatch")
    class GraphQLView(View):
        _schema = schema
        ide_enabled = ide
        # staticmethod: ``self.get_context(request)`` won't pass ``self`` to the
        # user callable; a subclass may override with a sync or async method.
        get_context = staticmethod(context_fn)

        async def post(
            self, request: HttpRequest, *args: Any, **kwargs: Any
        ) -> HttpResponse:
            resolver_ctx = self.get_context(request)
            if inspect.isawaitable(resolver_ctx):
                resolver_ctx = await resolver_ctx
            status_code, body = await execute_graphql_http(
                self._schema,
                content_type=request.META.get("CONTENT_TYPE", ""),
                body=request.body,
                context_value=resolver_ctx,
            )
            return HttpResponse(
                body,
                content_type="application/json",
                status=status_code,
            )

        async def get(
            self, request: HttpRequest, *args: Any, **kwargs: Any
        ) -> HttpResponse:
            if not self.ide_enabled:
                return HttpResponseNotAllowed(["POST"])
            return HttpResponse(GRAPHIQL_HTML, content_type="text/html")

    return GraphQLView
