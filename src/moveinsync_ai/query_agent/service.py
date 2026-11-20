"""Application service that exposes the LangGraph workflow through its contract."""

from .contracts import QueryAgent, QueryAgentError, QueryAnswer, QueryScope, SchemaContextRetriever, SqlExecutor, SqlGenerator, SqlValidator
from .graph import build_query_graph


class LangGraphQueryAgent:
    def __init__(self, retriever: SchemaContextRetriever, generator: SqlGenerator, validator: SqlValidator, executor: SqlExecutor):
        self._graph = build_query_graph(retriever, generator, validator, executor)

    def ask(self, question: str, scope: QueryScope) -> QueryAnswer:
        state = self._graph.invoke({"question": question, "scope": scope})
        if state.get("error"):
            raise QueryAgentError(state["error"])
        return QueryAnswer(state["answer"], state["sql"], state["result_summary"], state["result"])
