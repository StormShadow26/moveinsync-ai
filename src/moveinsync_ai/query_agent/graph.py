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
    result: QueryResult
    validation_error: str
    error: str
    attempts: int


def build_query_graph(retriever: SchemaContextRetriever, generator: SqlGenerator, validator: SqlValidator, executor: SqlExecutor):
    def validate_question(state: QueryState) -> QueryState:
        question = state["question"].strip()
        if not question or len(question) > 10_000:
            return {"error": "Please enter a question of 1 to 10,000 characters."}
        if "active trip" in question.lower():
            return {"error": "What should count as an active trip: scheduled trips only, or completed and delayed trips too?"}
        return {"question": question}

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
        return {"error": state.get("error", "I couldn't complete that data request just now. Please try again.")}

    def execute(state: QueryState) -> QueryState:
        try:
            result = executor.execute(state["sql"], state["scope"])
            return {"result": result, "result_summary": f"Returned {len(result.rows)} row(s)."}
        except Exception as error:
            original = getattr(error, "orig", error)
            if getattr(original, "sqlstate", None) == "57014":
                return {"error": "The query timed out. Try a shorter date range or a more specific question."}
            return {"error": "The data query could not be completed. Try a more specific question."}

    def summarize(state: QueryState) -> QueryState:
        if not state["result"].rows:
            return {"answer": "No matching rows were found. Try a different date range or filter."}
        return {"answer": generator.summarize(state["question"], state["result"])}

    graph = StateGraph(QueryState)
    graph.add_node("validate_question", validate_question)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate)
    graph.add_node("execute", execute)
    graph.add_node("summarize", summarize)
    graph.add_node("failed", failed)
    graph.add_edge(START, "validate_question")
    graph.add_conditional_edges("validate_question", lambda state: "done" if state.get("error") else "retrieve", {"done": END, "retrieve": "retrieve"})
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges("validate", after_validation, {"generate": "generate", "execute": "execute", "failed": "failed"})
    graph.add_conditional_edges("execute", lambda state: "failed" if state.get("error") else "summarize", {"failed": "failed", "summarize": "summarize"})
    graph.add_edge("summarize", END)
    graph.add_edge("failed", END)
    return graph.compile()
