"""Tests for maintenance with a fake connection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from streampulse_loader.maintenance import old_ci_schemas, table_stats


class FakeCursor:
    def __init__(self, rows, description=None):
        self.rows = rows
        self.description = description
        self.statements: list[str] = []

    def execute(self, sql):
        self.statements.append(sql)
        return self

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_ = cursor

    def cursor(self):
        return self.cursor_


def test_old_ci_schemas_keeps_only_old_ci_names():
    now = datetime.now(UTC)
    rows = [
        (now - timedelta(days=30), "CI_PR_12", "x"),
        (now - timedelta(days=1), "CI_PR_13", "x"),
        (now - timedelta(days=30), "CIVIC", "x"),
        (now - timedelta(days=30), "CI_PR_11", "x"),
    ]
    cursor = FakeCursor(rows, description=[("created_on",), ("name",), ("kind",)])
    names = old_ci_schemas(FakeConnection(cursor), "STREAMPULSE_DEV", older_than_days=7)
    assert names == ["CI_PR_11", "CI_PR_12"]
    assert "in database STREAMPULSE_DEV" in cursor.statements[0]


def test_table_stats_reads_the_environment_database():
    cursor = FakeCursor([("RAW", "CUSTOMERS", 10, 2048)])
    assert table_stats(FakeConnection(cursor), "STREAMPULSE_DEV") == [
        ("RAW", "CUSTOMERS", 10, 2048)
    ]
    assert "from STREAMPULSE_DEV.information_schema.tables" in cursor.statements[0]
