"""Provision the ClickHouse connection and starter dashboard in Metabase."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProvisionError(RuntimeError):
    """Raised when Metabase provisioning cannot continue safely."""


def load_env_file(path: Path) -> None:
    """Load a simple Compose-style env file without overwriting process values."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ProvisionError(f"Set {name} in .env before provisioning Metabase.")
    return value


def _items(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        for key in ("data", "items"):
            if isinstance(response.get(key), list):
                return response[key]
    raise ProvisionError("Metabase returned an unexpected collection response.")


class MetabaseClient:
    def __init__(self, base_url: str, sensitive_values: tuple[str, ...] = ()) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id: str | None = None
        self.sensitive_values = tuple(value for value in sensitive_values if value)

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.session_id:
            headers["X-Metabase-Session"] = self.session_id

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310 - URL is operator-owned
                response_body = response.read()
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            for value in self.sensitive_values:
                message = message.replace(value, "***")
            raise ProvisionError(
                f"Metabase {method} {path} failed with HTTP {exc.code}: {message}"
            ) from exc
        except URLError as exc:
            raise ProvisionError(f"Cannot reach Metabase at {self.base_url}: {exc.reason}") from exc

        if not response_body:
            return None
        return json.loads(response_body)

    def authenticate(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> None:
        properties = self.request("GET", "/api/session/properties")
        if not properties.get("has-user-setup"):
            setup_token = properties.get("setup-token")
            if not setup_token:
                raise ProvisionError("Metabase has no setup token and no configured administrator.")
            response = self.request(
                "POST",
                "/api/setup",
                {
                    "token": setup_token,
                    "user": {
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "password": password,
                    },
                    "prefs": {"site_name": "Portable Data Platform", "site_locale": "en"},
                },
            )
        else:
            response = self.request(
                "POST",
                "/api/session",
                {"username": email, "password": password},
            )
        self.session_id = response.get("id")
        if not self.session_id:
            raise ProvisionError("Metabase authenticated but did not return a session ID.")


@dataclass(frozen=True)
class CardSpec:
    name: str
    description: str
    display: str
    sql: str
    visualization_settings: dict[str, Any]
    row: int
    col: int
    size_x: int
    size_y: int


SEGMENT_TAG = {
    "segment": {
        "id": "customer-segment",
        "name": "segment",
        "display-name": "Segment",
        "type": "text",
        "required": False,
    }
}

CURRENCY_COLUMN = json.dumps(["name", "lifetime_value"], separators=(",", ":"))
CURRENCY_SETTINGS = {
    "number_style": "currency",
    "currency": "USD",
    "currency_style": "symbol",
    "decimals": 2,
}


def dashboard_card_specs(database: str) -> list[CardSpec]:
    source = f"`{database}`.`customer_activity`"
    filtered = f"FROM {source} WHERE 1 = 1 [[AND segment = {{{{segment}}}}]]"
    return [
        CardSpec(
            name="Customer Overview — Total Customers",
            description="Number of customers represented in the customer_activity mart.",
            display="scalar",
            sql=f"SELECT count() AS customers {filtered}",
            visualization_settings={},
            row=0,
            col=0,
            size_x=6,
            size_y=3,
        ),
        CardSpec(
            name="Customer Overview — Active Customers",
            description="Customers with at least one recorded order or event.",
            display="scalar",
            sql=(
                "SELECT countIf(order_count > 0 OR event_count > 0) AS active_customers "
                f"{filtered}"
            ),
            visualization_settings={},
            row=0,
            col=6,
            size_x=6,
            size_y=3,
        ),
        CardSpec(
            name="Customer Overview — Total Orders",
            description="Sum of customer order counts in the customer_activity mart.",
            display="scalar",
            sql=f"SELECT sum(order_count) AS orders {filtered}",
            visualization_settings={},
            row=0,
            col=12,
            size_x=6,
            size_y=3,
        ),
        CardSpec(
            name="Customer Overview — Lifetime Value",
            description="Total customer lifetime value in USD.",
            display="scalar",
            sql=f"SELECT toFloat64(sum(lifetime_value)) AS lifetime_value {filtered}",
            visualization_settings={
                "scalar.field": "lifetime_value",
                "column_settings": {CURRENCY_COLUMN: CURRENCY_SETTINGS},
            },
            row=0,
            col=18,
            size_x=6,
            size_y=3,
        ),
        CardSpec(
            name="Customer Overview — Lifetime Value by Segment",
            description="Customer lifetime value grouped by segment.",
            display="bar",
            sql=(
                "SELECT segment, toFloat64(sum(lifetime_value)) AS lifetime_value "
                f"{filtered} GROUP BY segment ORDER BY lifetime_value DESC"
            ),
            visualization_settings={
                "graph.dimensions": ["segment"],
                "graph.metrics": ["lifetime_value"],
                "graph.show_values": True,
                "column_settings": {CURRENCY_COLUMN: CURRENCY_SETTINGS},
            },
            row=3,
            col=0,
            size_x=12,
            size_y=6,
        ),
        CardSpec(
            name="Customer Overview — Activity by Segment",
            description="Orders and tracked events grouped by customer segment.",
            display="bar",
            sql=(
                "SELECT segment, sum(order_count) AS orders, sum(event_count) AS events "
                f"{filtered} GROUP BY segment ORDER BY segment"
            ),
            visualization_settings={
                "graph.dimensions": ["segment"],
                "graph.metrics": ["orders", "events"],
                "graph.show_values": True,
            },
            row=3,
            col=12,
            size_x=12,
            size_y=6,
        ),
        CardSpec(
            name="Customer Overview — Customer Detail",
            description="Customer-level order, activity, and lifetime-value detail.",
            display="table",
            sql=(
                "SELECT customer_id, name, segment, event_count, last_event_at, order_count, "
                "toFloat64(lifetime_value) AS lifetime_value, last_order_at "
                f"{filtered} ORDER BY lifetime_value DESC, customer_id"
            ),
            visualization_settings={
                "column_settings": {CURRENCY_COLUMN: CURRENCY_SETTINGS},
            },
            row=9,
            col=0,
            size_x=24,
            size_y=7,
        ),
    ]


def native_dataset_query(database_id: int, sql: str) -> dict[str, Any]:
    return {
        "database": database_id,
        "type": "native",
        "native": {"query": sql, "template-tags": SEGMENT_TAG},
    }


def find_named(items: list[dict[str, Any]], name: str, collection_id: int | None = None) -> Any:
    for item in items:
        if item.get("name") != name or item.get("archived", False):
            continue
        if collection_id is None or item.get("collection_id") == collection_id:
            return item
    return None


def upsert_database(client: MetabaseClient, details: dict[str, Any]) -> int:
    validate_payload = {"details": {"engine": "clickhouse", "details": details}}
    client.request("POST", "/api/database/validate", validate_payload)

    name = "ClickHouse Analytics"
    databases = _items(client.request("GET", "/api/database"))
    existing = find_named(databases, name)
    payload = {
        "name": name,
        "engine": "clickhouse",
        "details": details,
        "auto_run_queries": True,
        "refingerprint": False,
    }
    if existing:
        database = client.request("PUT", f"/api/database/{existing['id']}", payload)
    else:
        database = client.request("POST", "/api/database", payload)
    database_id = int(database.get("id", existing["id"] if existing else 0))
    client.request("POST", f"/api/database/{database_id}/sync_schema")
    return database_id


def upsert_collection(client: MetabaseClient) -> int:
    name = "Portable Data Platform"
    collections = _items(
        client.request("GET", "/api/collection", query={"exclude-other-user-collections": "true"})
    )
    existing = find_named(collections, name)
    if existing:
        return int(existing["id"])
    collection = client.request(
        "POST",
        "/api/collection",
        {
            "name": name,
            "description": "Governed analytics generated from the dbt marts in ClickHouse.",
        },
    )
    return int(collection["id"])


def upsert_cards(
    client: MetabaseClient,
    database_id: int,
    collection_id: int,
    specs: list[CardSpec],
) -> list[tuple[CardSpec, int]]:
    cards = _items(client.request("GET", "/api/card"))
    provisioned: list[tuple[CardSpec, int]] = []
    for spec in specs:
        payload = {
            "name": spec.name,
            "description": spec.description,
            "collection_id": collection_id,
            "type": "question",
            "dataset_query": native_dataset_query(database_id, spec.sql),
            "display": spec.display,
            "visualization_settings": spec.visualization_settings,
            "parameters": [],
        }
        existing = find_named(cards, spec.name, collection_id)
        if existing:
            card = client.request("PUT", f"/api/card/{existing['id']}", payload)
        else:
            card = client.request("POST", "/api/card", payload)
        provisioned.append((spec, int(card.get("id", existing["id"] if existing else 0))))
    return provisioned


def upsert_dashboard(
    client: MetabaseClient,
    collection_id: int,
    cards: list[tuple[CardSpec, int]],
) -> int:
    name = "Customer Overview"
    dashboards = _items(client.request("GET", "/api/dashboard"))
    existing = find_named(dashboards, name, collection_id)
    if existing:
        dashboard_id = int(existing["id"])
        current = client.request("GET", f"/api/dashboard/{dashboard_id}")
    else:
        current = client.request(
            "POST",
            "/api/dashboard",
            {
                "name": name,
                "collection_id": collection_id,
                "description": "Customer reach, activity, orders, and lifetime value from dbt.",
            },
        )
        dashboard_id = int(current["id"])

    existing_dashcards = {
        item.get("card_id"): item for item in current.get("dashcards", []) if item.get("card_id")
    }
    dashcards = []
    for index, (spec, card_id) in enumerate(cards, start=1):
        current_dashcard = existing_dashcards.get(card_id, {})
        dashcards.append(
            {
                "id": current_dashcard.get("id", -index),
                "card_id": card_id,
                "row": spec.row,
                "col": spec.col,
                "size_x": spec.size_x,
                "size_y": spec.size_y,
                "parameter_mappings": [
                    {
                        "card_id": card_id,
                        "parameter_id": "customer-segment",
                        "target": ["variable", ["template-tag", "segment"]],
                    }
                ],
                "series": [],
                "visualization_settings": {},
            }
        )

    dashboard = client.request(
        "PUT",
        f"/api/dashboard/{dashboard_id}",
        {
            "name": name,
            "description": "Customer reach, activity, orders, and lifetime value from dbt.",
            "collection_id": collection_id,
            "width": "fixed",
            "parameters": [
                {
                    "id": "customer-segment",
                    "name": "Segment",
                    "slug": "segment",
                    "type": "string/=",
                    "sectionId": "string",
                    "required": False,
                }
            ],
            "dashcards": dashcards,
        },
    )
    return int(dashboard.get("id", dashboard_id))


def validate_dashboard(
    client: MetabaseClient,
    dashboard_id: int,
    cards: list[tuple[CardSpec, int]],
) -> None:
    for spec, card_id in cards:
        result = client.request(
            "POST",
            f"/api/card/{card_id}/query",
            {"ignore_cache": True, "dashboard_id": dashboard_id},
        )
        rows = result.get("data", {}).get("rows")
        if not isinstance(rows, list):
            raise ProvisionError(f"Question did not return rows: {spec.name}")

    dashboard = client.request("GET", f"/api/dashboard/{dashboard_id}")
    if len(dashboard.get("dashcards", [])) != len(cards):
        raise ProvisionError("Dashboard card count does not match the provisioned questions.")


def provision(env_file: Path) -> str:
    load_env_file(env_file)
    email = require_env("METABASE_ADMIN_EMAIL")
    password = require_env("METABASE_ADMIN_PASSWORD")
    clickhouse_password = os.getenv(
        "METABASE_CLICKHOUSE_PASSWORD", "CHANGE_ME_metabase_clickhouse"
    )
    base_url = os.getenv("METABASE_URL", "http://127.0.0.1:3001")
    database_name = os.getenv("CLICKHOUSE_DB", "analytics")

    client = MetabaseClient(base_url, sensitive_values=(password, clickhouse_password))
    client.authenticate(
        email=email,
        password=password,
        first_name=os.getenv("METABASE_ADMIN_FIRST_NAME", "Platform"),
        last_name=os.getenv("METABASE_ADMIN_LAST_NAME", "Admin"),
    )
    database_id = upsert_database(
        client,
        {
            "host": os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            "port": int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123")),
            "user": os.getenv("METABASE_CLICKHOUSE_USER", "metabase"),
            "password": clickhouse_password,
            "enable-multiple-db": False,
            "dbname": database_name,
            "ssl": False,
            "tunnel-enabled": False,
        },
    )
    collection_id = upsert_collection(client)
    cards = upsert_cards(
        client,
        database_id=database_id,
        collection_id=collection_id,
        specs=dashboard_card_specs(database_name),
    )
    dashboard_id = upsert_dashboard(client, collection_id, cards)
    validate_dashboard(client, dashboard_id, cards)
    return f"{base_url.rstrip('/')}/dashboard/{dashboard_id}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision the ClickHouse connection and Customer Overview dashboard."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Compose-style environment file (default: .env)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        dashboard_url = provision(args.env_file)
    except ProvisionError as exc:
        print(f"Metabase provisioning failed: {exc}", file=sys.stderr)
        return 1
    print(f"Metabase dashboard ready: {dashboard_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
