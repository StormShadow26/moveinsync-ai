"""Read-only SQL policy enforcement independent of model behavior."""

from sqlglot import exp, parse

from .contracts import SqlValidationError, SqlValidator


ALLOWED_TABLES = {"companies", "vendors", "vehicles", "routes", "employees", "trips", "trip_bookings", "cities", "drivers", "shifts", "rosters", "roster_entries", "invoices", "invoice_lines", "trip_events"}
ALLOWED_FUNCTIONS = {
    "ABS", "AND", "AVG", "CASE", "CAST", "CEIL", "CEILING", "COALESCE", "COUNT", "DATE", "DATE_TRUNC", "IF", "NOT", "OR",
    "EXTRACT", "FLOOR", "GREATEST", "LEAST", "LOWER", "MAX", "MIN", "NULLIF", "ROUND",
    "SUM", "TRIM", "UPPER",
}
FORBIDDEN_NODES = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Merge,
    exp.Update,
)


class ReadOnlySqlValidator:
    """Allows one SELECT statement over reviewed operational tables only."""

    def validate(self, sql: str) -> str:
        candidate = sql.strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        try:
            statements = parse(candidate, read="postgres")
        except Exception as error:
            raise SqlValidationError("Generated SQL could not be parsed") from error
        if len(statements) != 1 or not isinstance(statements[0], exp.Select):
            raise SqlValidationError("Only one SELECT statement is allowed")
        statement = statements[0]
        if any(isinstance(node, FORBIDDEN_NODES) for node in statement.walk()):
            raise SqlValidationError("Generated SQL contains a forbidden operation")
        tables = {table.name for table in statement.find_all(exp.Table)}
        if not tables or not tables <= ALLOWED_TABLES:
            raise SqlValidationError("Generated SQL references a table outside the transport schema")
        if any(table.catalog or (table.db and table.db != "public") for table in statement.find_all(exp.Table)):
            raise SqlValidationError("Only public transport tables are allowed")
        if any(data_type.this == exp.DataType.Type.USERDEFINED for data_type in statement.find_all(exp.DataType)):
            raise SqlValidationError("Custom data types are not allowed")
        if any(statement.find_all(exp.Operator)):
            raise SqlValidationError("Custom operators are not allowed")
        if any(join.args.get("kind", "").upper() == "CROSS" or not join.args.get("on") and not join.args.get("using") for join in statement.find_all(exp.Join)):
            raise SqlValidationError("Cross joins are not allowed")
        for function in statement.find_all(exp.Func):
            name = function.name.upper() if isinstance(function, exp.Anonymous) else function.sql_name().upper()
            if name not in ALLOWED_FUNCTIONS or isinstance(function.parent, exp.Dot):
                raise SqlValidationError("Generated SQL contains an unapproved function")
        if any(select.args.get("locks") for select in statement.find_all(exp.Select)):
            raise SqlValidationError("Row locking is not allowed")
        if any(select.args.get("into") for select in statement.find_all(exp.Select)):
            raise SqlValidationError("SELECT INTO is not allowed")
        for table in statement.find_all(exp.Table):
            table.set("db", exp.to_identifier("public"))
        return statement.sql(dialect="postgres")
