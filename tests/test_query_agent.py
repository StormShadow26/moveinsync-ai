from moveinsync_ai.query_agent.contracts import QueryResult, QueryScope, SqlValidationError
from moveinsync_ai.query_agent.service import LangGraphQueryAgent
from moveinsync_ai.query_agent.sql_validator import ReadOnlySqlValidator


class SchemaRetriever:
    def retrieve(self, question: str) -> str:
        return "trips(id, trip_number)"


class Generator:
    def generate_sql(self, question: str, schema_context: str, previous_error: str | None = None) -> str:
        return "SELECT trip_number FROM trips"

    def summarize(self, question: str, result: QueryResult) -> str:
        return f"Found {len(result.rows)} trip."


class Executor:
    def execute(self, sql: str, scope: QueryScope) -> QueryResult:
        return QueryResult(["trip_number"], [{"trip_number": "NBH-101"}])


def test_validator_allows_single_select_from_transport_tables() -> None:
    assert ReadOnlySqlValidator().validate("SELECT trip_number FROM trips") == "SELECT trip_number FROM trips"


def test_validator_rejects_writes_and_unreviewed_tables() -> None:
    validator = ReadOnlySqlValidator()
    for sql in ("DELETE FROM trips", "SELECT * FROM users", "SELECT * INTO exported_trips FROM trips", "SELECT * FROM trips; SELECT * FROM routes"):
        try:
            validator.validate(sql)
        except SqlValidationError:
            continue
        raise AssertionError(f"Expected SQL to be rejected: {sql}")


def test_langgraph_agent_returns_a_validated_answer() -> None:
    agent = LangGraphQueryAgent(SchemaRetriever(), Generator(), ReadOnlySqlValidator(), Executor())
    answer = agent.ask("Show trips", QueryScope(1, 3, "single_company"))
    assert answer.content == "Found 1 trip."
    assert answer.generated_sql == "SELECT trip_number FROM trips"
    assert answer.result_summary == "Returned 1 row(s)."
