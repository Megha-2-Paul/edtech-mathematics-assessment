"""Safe SQLAlchemy database URL construction."""

from sqlalchemy.engine import URL


def build_database_url(
    *,
    host: str,
    port: str | int,
    database: str,
    username: str,
    password: str,
    override: str | None = None,
) -> URL | str:
    """Build a MySQL URL safely, preserving explicit URL overrides."""
    if override:
        return override

    return URL.create(
        drivername="mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=int(port),
        database=database,
        query={"charset": "utf8mb4"},
    )
