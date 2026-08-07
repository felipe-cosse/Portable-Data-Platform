from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "data" / "inbox" / "orders.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "order_id": [1001, 1002, 1003],
            "customer_id": [1, 2, 1],
            "amount": [125.50, 42.00, 18.75],
            "ordered_at": [
                "2026-08-01T10:00:00Z",
                "2026-08-02T13:30:00Z",
                "2026-08-04T17:15:00Z",
            ],
        }
    )
    pq.write_table(table, output)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
