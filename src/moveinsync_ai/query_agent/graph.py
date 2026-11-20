"""Explicit LangGraph workflow for safe natural-language data questions."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .contracts import QueryResult, QueryScope, SchemaContextRetriever, SqlExecutor, SqlGenerator, SqlValidator


class QueryState(TypedDict, total=False):
    question: str
    scope: QueryScope
    schema_context: str
    sql: str
    answer: str
    result_summary: str
    rows: list[dict]
    validation_error: str
    error: str
    attempts: int


def build_query_graph(retriever: SchemaContextRetriever, generator: SqlGenerator, validator: SqlValidator, executor: SqlExecutor):
    def retrieve(state: QueryState) -> QueryState:
        return {"schema_context": retriever.retrieve(state["question"])}

    def generate(state: QueryState) -> QueryState:
        return {
            "sql": generator.generate_sql(state["question"], state["schema_context"], state.get("validation_error")),
            "attempts": state.get("attempts", 0) + 1,
            "validation_error": "",
        }

    def validate(state: QueryState) -> QueryState:
        try:
            return {"sql": validator.validate(state["sql"])}
        except Exception as error:
            return {"validation_error": str(error)}

    def after_validation(state: QueryState) -> str:
        if state.get("validation_error"):
            return "generate" if state["attempts"] < 2 else "failed"
        return "execute"

    def failed(state: QueryState) -> QueryState:
        if state.get("validation_error"):
            return {
                "error": (
                    "I can help with transport operations such as trips, routes, vehicles, vendors, "
                    "bookings, no-shows, occupancy, and costs. Please rephrase your question around that data."
                )
            }
        return {"error": "I couldn't complete that data request just now. Please try again."}

    def execute(state: QueryState) -> QueryState:
        try:
            result = executor.execute(state["sql"], state["scope"])
            return {"rows": result.rows, "result_summary": f"Returned {len(result.rows)} row(s)."}
        except Exception as error:
            return {"error": "The data query could not be completed."}

    def summarize(state: QueryState) -> QueryState:
        return {"answer": generator.summarize(state["question"], QueryResult([], state["rows"]))}

    graph = StateGraph(QueryState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate)
    graph.add_node("execute", execute)
    graph.add_node("summarize", summarize)
    graph.add_node("failed", failed)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges("validate", after_validation, {"generate": "generate", "execute": "execute", "failed": "failed"})
    graph.add_conditional_edges("execute", lambda state: "failed" if state.get("error") else "summarize", {"failed": "failed", "summarize": "summarize"})
    graph.add_edge("summarize", END)
    graph.add_edge("failed", END)
    return graph.compile()
