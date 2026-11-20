"""Compare live model answers with retrieved and full-schema context; opt-in."""
import json
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from moveinsync_ai.database.rls import tenant_scope_setter
from moveinsync_ai.query_agent.contracts import QueryScope
from moveinsync_ai.query_agent.groq import GroqChatModel, GroqSqlGenerator
from moveinsync_ai.query_agent.schema_retrieval import ChromaSchemaRetriever, CuratedSchemaRetriever
from moveinsync_ai.query_agent.sql_executor import RlsSqlExecutor
from moveinsync_ai.query_agent.sql_validator import ReadOnlySqlValidator
from run import CASES


def main():
    model = GroqSqlGenerator(GroqChatModel(os.getenv("GROQ_API_KEY"), os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")))
    retriever = ChromaSchemaRetriever()
    full_schema = CuratedSchemaRetriever().retrieve("unrecognized vocabulary")
    with Session(create_engine(os.environ["DATABASE_URL"])) as session:
        executor = RlsSqlExecutor(session, tenant_scope_setter, 100, 10)
        for case_id, question, _, companies, company, expected in CASES:
            for mode in ("chroma", "full"):
                context = retriever.retrieve(question) if mode == "chroma" else full_schema
                try:
                    sql = ReadOnlySqlValidator().validate(model.generate_sql(question, context))
                    scope = QueryScope(1, company, "single_company" if company else "all_companies", companies)
                    rows = executor.execute(sql, scope).rows
                    actual = rows if expected == [] or len(rows) != 1 or len(rows[0]) != 1 else next(iter(rows[0].values()))
                    actual = float(actual) if actual is not None and not isinstance(actual, list) else actual
                    passed = actual == expected
                    notes = f"{mode}; schema context {len(context)} characters"
                except Exception as error:
                    session.rollback()
                    actual, passed, notes = None, False, f"{mode}; {type(error).__name__}; schema context {len(context)} characters"
                print(json.dumps({"id": f"{case_id}-{mode}", "input": question, "expected": expected, "actual": actual, "pass": passed, "notes": notes}, default=str), flush=True)


if __name__ == "__main__":
    main()
