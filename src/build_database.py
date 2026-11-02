
import argparse
import sqlite3
import sys
import pandas as pd
from config import RAW_DIR, SAMPLE_DIR, DB_PATH, SQL_DIR, CSV_FILES


def load_csvs(conn, data_dir):
    missing = [f for f in CSV_FILES.values() if not (data_dir / f).exists()]
    if missing:
        sys.exit(
            "\nMissing CSV files in %s:\n  - %s\n\nDownload the dataset from "
            "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce " % (data_dir, "\n  - ".join(missing)))
    for table, fname in CSV_FILES.items():
        df = pd.read_csv(data_dir / fname)
        df.to_sql(table, conn, if_exists="replace", index=False, chunksize=50_000)
        print(f"  loaded {table:<22} {len(df):>9,} rows")


def create_indexes(conn):
    stmts = [
        "CREATE INDEX IF NOT EXISTS ix_orders_id ON orders(order_id)",
        "CREATE INDEX IF NOT EXISTS ix_orders_cust ON orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_cust_id ON customers(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_items_order ON order_items(order_id)",
        "CREATE INDEX IF NOT EXISTS ix_items_seller ON order_items(seller_id)",
        "CREATE INDEX IF NOT EXISTS ix_items_prod ON order_items(product_id)",
        "CREATE INDEX IF NOT EXISTS ix_pay_order ON order_payments(order_id)",
        "CREATE INDEX IF NOT EXISTS ix_rev_order ON order_reviews(order_id)",
        "CREATE INDEX IF NOT EXISTS ix_prod_id ON products(product_id)",
        "CREATE INDEX IF NOT EXISTS ix_sell_id ON sellers(seller_id)",
    ]
    for s in stmts:
        conn.execute(s)


def data_quality_checks(conn):
    """Fail loudly if joins fan out or key assumptions break."""
    q = lambda sql: conn.execute(sql).fetchone()[0]
    n_orders = q("SELECT COUNT(*) FROM orders")
    n_view = q("SELECT COUNT(*) FROM v_orders_enriched")
    assert n_orders == n_view, f"v_orders_enriched has {n_view} rows but orders has {n_orders} (join fan-out!)"
    raw_rev = q("SELECT SUM(price) FROM order_items")
    view_rev = q("SELECT SUM(items_revenue) FROM v_orders_enriched")
    assert abs(raw_rev - view_rev) < 0.01, "Revenue in view does not reconcile with order_items"
    dup_reviews = q("SELECT COUNT(*) FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*)>1)")
    multi_pay = q("SELECT COUNT(*) FROM (SELECT order_id FROM order_payments GROUP BY order_id HAVING COUNT(*)>1)")
    print("\nData-quality checks")
    print(f"  [ok] one row per order in v_orders_enriched ({n_view:,})")
    print(f"  [ok] revenue reconciles with raw order_items ({raw_rev:,.2f})")
    print(f"  [info] orders with multiple reviews handled via window function: {dup_reviews:,}")
    print(f"  [info] orders with split payments aggregated: {multi_pay:,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="use synthetic data (smoke test only)")
    args = ap.parse_args()
    data_dir = SAMPLE_DIR if args.sample else RAW_DIR
    if args.sample and not (SAMPLE_DIR / CSV_FILES["orders"]).exists():
        from generate_sample_data import generate
        generate()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    print(f"Loading CSVs from {data_dir} ...")
    load_csvs(conn, data_dir)
    create_indexes(conn)
    conn.executescript((SQL_DIR / "01_views.sql").read_text(encoding="utf-8"))
    data_quality_checks(conn)
    conn.commit()
    conn.close()
    print(f"\nDatabase ready: {DB_PATH}")


if __name__ == "__main__":
    main()
