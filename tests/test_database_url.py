import pytest

from sqlalchemy.engine import URL

from database_url import build_database_url


@pytest.mark.parametrize(
    "password",
    [
        "contains@at",
        "contains:colon",
        "contains/slash",
        "contains?question",
        "contains#hash",
        "contains%percent",
        "contains&ampersand",
        "contains+plus",
        "contains$dollar",
        "contains!exclamation",
        "contains'quote",
        'contains"doublequote',
        r"contains\backslash",
        "contains[brackets]",
        "contains{braces}",
        "contains(parentheses)",
        "contains,comma;semicolon=equals",
        "contains<angle>^caret`backtick~tilde",
        "mixed@:/?#%&+$!'\"\\[]{}(),;=<>^`~",
    ],
)
def test_special_characters_round_trip_in_password(password):
    url = build_database_url(
        host="127.0.0.1",
        port="3306",
        database="improvia_dev",
        username="synthetic_user",
        password=password,
    )

    assert isinstance(url, URL)
    assert url.password == password
    assert url.host == "127.0.0.1"
    assert url.port == 3306
    assert url.database == "improvia_dev"
    assert url.username == "synthetic_user"
    assert url.query["charset"] == "utf8mb4"


def test_explicit_database_url_override_is_preserved():
    override = (
        "mysql+pymysql://synthetic_user:synthetic_password"
        "@example.invalid:3307/override_db?charset=utf8mb4"
    )

    result = build_database_url(
        host="127.0.0.1",
        port="3306",
        database="improvia_dev",
        username="local_user",
        password="local_password",
        override=override,
    )

    assert result == override
    assert isinstance(result, str)


def test_empty_override_uses_safe_url_builder():
    result = build_database_url(
        host="127.0.0.1",
        port="3306",
        database="improvia_dev",
        username="synthetic_user",
        password="synthetic@password",
        override="",
    )

    assert isinstance(result, URL)
    assert result.password == "synthetic@password"
    assert result.database == "improvia_dev"
