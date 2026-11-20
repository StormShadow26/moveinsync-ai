from moveinsync_ai.query_agent.contracts import QueryAgentError, QueryProviderError, QueryResult, QueryScope, SqlValidationError
from moveinsync_ai.query_agent.groq import GroqSqlGenerator
from moveinsync_ai.query_agent.schema_retrieval import CuratedSchemaRetriever
from moveinsync_ai.query_agent.service import LangGraphQueryAgent
from moveinsync_ai.query_agent.sql_validator import ReadOnlySqlValidator
from unittest.mock import MagicMock, patch


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
    assert ReadOnlySqlValidator().validate("SELECT trip_number FROM trips") == "SELECT trip_number FROM public.trips"
    assert "WHERE" in ReadOnlySqlValidator().validate("SELECT id FROM trips WHERE status = 'completed' AND vendor_cost > 0")


def test_validator_rejects_writes_and_unreviewed_tables() -> None:
    validator = ReadOnlySqlValidator()
    for sql in (
        "DELETE FROM trips", "SELECT * FROM users", "SELECT * INTO exported_trips FROM trips",
        "SELECT * FROM trips; SELECT * FROM routes", "SELECT * FROM trips CROSS JOIN employees",
        "SELECT * FROM trips, employees", "SELECT * FROM other.trips",
        "SELECT set_config('app.access_scope', 'all_companies', true) FROM trips",
        "SELECT pg_catalog.set_config('app.company_id', '2', true) FROM trips",
        "SELECT pg_sleep(1) FROM trips", "SELECT CAST(status AS public.custom_type) FROM trips",
        "SELECT 1 OPERATOR(public.evil) 2 FROM trips",
    ):
        try:
            validator.validate(sql)
        except SqlValidationError:
            continue
        raise AssertionError(f"Expected SQL to be rejected: {sql}")


def test_langgraph_agent_returns_a_validated_answer() -> None:
    agent = LangGraphQueryAgent(SchemaRetriever(), Generator(), ReadOnlySqlValidator(), Executor())
    answer = agent.ask("Show trips", QueryScope(1, 3, "single_company", [3]))
    assert answer.content == "Found 1 trip."
    assert answer.generated_sql == "SELECT trip_number FROM public.trips"
    assert answer.result_summary == "Returned 1 row(s)."
    assert answer.result.columns == ["trip_number"]
    assert answer.result.rows == [{"trip_number": "NBH-101"}]


def test_schema_retrieval_selects_topics_and_joins_with_fallback() -> None:
    retriever = CuratedSchemaRetriever()
    trips = retriever.retrieve("Show trips")
    assert "trips(id," in trips and "employees(id," not in trips
    occupancy = retriever.retrieve("What is vehicle occupancy by route?")
    assert all(table in occupancy for table in ("vehicles(id,", "routes(id,", "trips(id,", "trip_bookings(id,"))
    assert "Occupancy =" in occupancy and "trips.vehicle_id -> vehicles.id" in occupancy
    assert "trip_bookings(id," in retriever.retrieve("How many no-shows?")
    assert "trip_bookings(id," in retriever.retrieve("Employees by route")
    assert "trips.company_id -> companies.id" in retriever.retrieve("Trips by company")
    assert "employees(id," in retriever.retrieve("Give me an overview")
    assert "vendors(id," in retriever.retrieve("How many trips use Fleet 1?")


def test_question_validation_stops_before_retrieval() -> None:
    class NeverRetrieve:
        def retrieve(self, question: str) -> str:
            raise AssertionError("Invalid questions must not reach retrieval")

    agent = LangGraphQueryAgent(NeverRetrieve(), Generator(), ReadOnlySqlValidator(), Executor())
    for question in ("   ", "a" * 10_001):
        try:
            agent.ask(question, QueryScope(1, 3, "single_company", [3]))
        except QueryAgentError as error:
            assert "1 to 10,000" in str(error)
        else:
            raise AssertionError("Invalid question was accepted")


def test_sql_generator_requests_and_checks_structured_model_output() -> None:
    class Model:
        response = '{"sql": "SELECT id FROM trips", "reasoning_summary": "List trips"}'

        def complete(self, prompt: str, *, json_output: bool = False) -> str:
            assert json_output and "trips(id)" in prompt
            return self.response

    model = Model()
    generator = GroqSqlGenerator(model)
    assert generator.generate_sql("List trips", "trips(id)") == "SELECT id FROM trips"
    for response in ("not json", '{"sql": 3, "reasoning_summary": "x"}', '{"sql": "SELECT 1"}'):
        model.response = response
        try:
            generator.generate_sql("List trips", "trips(id)")
        except QueryProviderError:
            pass
        else:
            raise AssertionError("Malformed structured output was accepted")


def test_groq_chat_model_requests_json_only_when_needed() -> None:
    from moveinsync_ai.query_agent.groq import GroqChatModel

    client = MagicMock()
    client.chat.completions.create.return_value.choices[0].message.content = "response"
    with patch("moveinsync_ai.query_agent.groq.Groq", return_value=client):
        model = GroqChatModel("test-key", "test-model")
        assert model.complete("SQL as JSON", json_output=True) == "response"
        assert client.chat.completions.create.call_args.kwargs["response_format"] == {"type": "json_object"}
        model.complete("Summarize")
        assert "response_format" not in client.chat.completions.create.call_args.kwargs


def test_invalid_sql_gets_one_repair_attempt() -> None:
    class RepairingGenerator(Generator):
        errors = []

        def generate_sql(self, question, schema_context, previous_error=None):
            self.errors.append(previous_error)
            return "DELETE FROM trips" if previous_error is None else "SELECT trip_number FROM trips"

    generator = RepairingGenerator()
    answer = LangGraphQueryAgent(SchemaRetriever(), generator, ReadOnlySqlValidator(), Executor()).ask("Show trips", QueryScope(1, 3, "single_company", [3]))
    assert len(generator.errors) == 2 and generator.errors[1]
    assert answer.result.rows == [{"trip_number": "NBH-101"}]


def test_failed_sql_is_bounded_and_timeout_is_clear() -> None:
    class BadGenerator(Generator):
        calls = 0
        def generate_sql(self, question, schema_context, previous_error=None):
            self.calls += 1
            return "DELETE FROM trips"

    generator = BadGenerator()
    agent = LangGraphQueryAgent(SchemaRetriever(), generator, ReadOnlySqlValidator(), Executor())
    try:
        agent.ask("Show trips", QueryScope(1, 3, "single_company", [3]))
    except QueryAgentError:
        assert generator.calls == 2
    else:
        raise AssertionError("Unsafe SQL should fail")

    class Timeout(Exception):
        sqlstate = "57014"
    class TimedOutExecutor:
        def execute(self, sql, scope):
            raise Timeout()

    try:
        LangGraphQueryAgent(SchemaRetriever(), Generator(), ReadOnlySqlValidator(), TimedOutExecutor()).ask("Show trips", QueryScope(1, 3, "single_company", [3]))
    except QueryAgentError as error:
        assert "timed out" in str(error)
    else:
        raise AssertionError("Timeout should be reported")


def test_empty_results_and_ambiguous_active_trip_question() -> None:
    class EmptyExecutor:
        def execute(self, sql, scope):
            return QueryResult(["id"], [])

    agent = LangGraphQueryAgent(SchemaRetriever(), Generator(), ReadOnlySqlValidator(), EmptyExecutor())
    assert "No matching rows" in agent.ask("Show trips", QueryScope(1, 3, "single_company", [3])).content
    try:
        agent.ask("How many active trips?", QueryScope(1, 3, "single_company", [3]))
    except QueryAgentError as error:
        assert "What should count" in str(error)
    else:
        raise AssertionError("Ambiguous metric should need clarification")
