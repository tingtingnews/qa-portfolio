import pytest
import requests

@pytest.mark.db
class TestUserDatabase:

    def test_created_user_exists_in_db(self, db_connection, api_base_url):
        r = requests.post(f"{api_base_url}/users", json={"name": "Ting", "job": "QA Engineer"})
        assert r.status_code == 201
        api_user = r.json()

        db_connection.execute("INSERT INTO users (name, job) VALUES (?, ?)",
                              (api_user["name"], api_user["job"]))
        db_connection.commit()

        row = db_connection.execute("SELECT * FROM users WHERE name = ?",
                                    (api_user["name"],)).fetchone()
        assert row is not None
        assert row["name"] == api_user["name"]
        assert row["job"] == api_user["job"]

    def test_deleted_user_removed_from_db(self, db_connection, api_base_url):
        db_connection.execute("INSERT INTO users (name, job) VALUES ('Temp', 'Tester')")
        db_connection.commit()
        assert db_connection.execute("SELECT * FROM users WHERE name='Temp'").fetchone() is not None

        db_connection.execute("DELETE FROM users WHERE name='Temp'")
        db_connection.commit()
        assert db_connection.execute("SELECT * FROM users WHERE name='Temp'").fetchone() is None
