"""Read-only SQL policy enforcement independent of model behavior."""

from sqlglot import exp, parse

from .contracts import SqlValidationError, SqlValidator


ALLOWED_TABLES = {"companies", "vendors", "vehicles", "routes", "employees", "trips", "trip_bookings"}
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
        if statement.args.get("locks"):
            raise SqlValidationError("Row locking is not allowed")
        if statement.args.get("into"):
            raise SqlValidationError("SELECT INTO is not allowed")
        return statement.sql(dialect="postgres")
