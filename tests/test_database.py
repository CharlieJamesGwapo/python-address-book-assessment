import pytest

from address_book import database


def test_update_rejects_unrecognized_sql_columns(tmp_path):
    path = tmp_path / "addresses.sqlite3"
    database.initialize(path)
    with pytest.raises(ValueError, match="Invalid update fields"):
        database.update(path, 1, {"street = 'compromised' --": "bad"})
