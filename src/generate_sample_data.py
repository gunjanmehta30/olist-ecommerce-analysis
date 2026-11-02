
import numpy as np
import pandas as pd
from config import SAMPLE_DIR, CSV_FILES, STATE_NAMES


def generate(n_orders: int = 6000, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    states = list(STATE_NAMES)
    w = np.array([1] * len(states), dtype=float)
    w[states.index("SP")], w[states.index("RJ")], w[states.index("MG")] = 40, 12, 11
    w /= w.sum()
    cats_pt = ["cama_mesa_banho", "beleza_saude", "esporte_lazer", "informatica_acessorios",
               "relogios_presentes", "moveis_decoracao", "brinquedos", "telefonia", "automotivo", "livros_tecnicos"]
    cats_en = ["bed_bath_table", "health_beauty", "sports_leisure", "computers_accessories",
               "watches_gifts", "furniture_decor", "toys", "telephony", "auto", "books_technical"]

    pd.DataFrame({"product_category_name": cats_pt, "product_category_name_english": cats_en}) \
        .to_csv(SAMPLE_DIR / CSV_FILES["category_translation"], index=False)

    n_sell = 250
    sellers = pd.DataFrame({
        "seller_id": [f"s{i:04d}" for i in range(n_sell)],
        "seller_zip_code_prefix": rng.integers(1000, 99999, n_sell),
        "seller_city": "city",
        "seller_state": rng.choice(states, n_sell, p=w)})
    sellers.to_csv(SAMPLE_DIR / CSV_FILES["sellers"], index=False)

    n_prod = 1200
    products = pd.DataFrame({
        "product_id": [f"p{i:05d}" for i in range(n_prod)],
        "product_category_name": rng.choice(cats_pt, n_prod),
        "product_name_lenght": 40, "product_description_lenght": 500, "product_photos_qty": 2,
        "product_weight_g": 800, "product_length_cm": 20, "product_height_cm": 10, "product_width_cm": 15})
    products.to_csv(SAMPLE_DIR / CSV_FILES["products"], index=False)

    n_cust = int(n_orders * 0.95)
    cust = pd.DataFrame({
        "customer_unique_id": [f"u{i:06d}" for i in range(n_cust)],
        "customer_zip_code_prefix": rng.integers(1000, 99999, n_cust),
        "customer_city": "city",
        "customer_state": rng.choice(states, n_cust, p=w)})
    owner = np.concatenate([np.arange(n_cust), rng.integers(0, n_cust, n_orders - n_cust)])
    customers = cust.iloc[owner].reset_index(drop=True)
    customers.insert(0, "customer_id", [f"c{i:06d}" for i in range(n_orders)])
    customers.to_csv(SAMPLE_DIR / CSV_FILES["customers"], index=False)

    months = pd.date_range("2017-01-01", "2018-08-31", freq="D")
    day_w = np.linspace(1, 3, len(months))
    purchase = pd.Series(pd.to_datetime(rng.choice(months, n_orders, p=day_w / day_w.sum()))) \
        + pd.to_timedelta(rng.integers(0, 86400, n_orders), unit="s")
    est_days = rng.integers(14, 40, n_orders)
    seller_state = rng.choice(states, n_orders, p=w)
    cross = (seller_state != customers["customer_state"].values)
    base = rng.gamma(4, 2.5, n_orders) + 3 + cross * 5
    late_shock = (rng.random(n_orders) < 0.07) * rng.integers(5, 25, n_orders)
    actual_days = base + late_shock
    status = rng.choice(["delivered", "canceled", "shipped", "unavailable"], n_orders, p=[.965, .01, .015, .01])
    delivered = purchase + pd.to_timedelta(actual_days, unit="D")
    delivered = delivered.where(status == "delivered")
    estimated = (purchase + pd.to_timedelta(est_days, unit="D")).dt.normalize()
    orders = pd.DataFrame({
        "order_id": [f"o{i:06d}" for i in range(n_orders)],
        "customer_id": customers["customer_id"],
        "order_status": status,
        "order_purchase_timestamp": purchase,
        "order_approved_at": purchase + pd.Timedelta(hours=1),
        "order_delivered_carrier_date": purchase + pd.Timedelta(days=2),
        "order_delivered_customer_date": delivered,
        "order_estimated_delivery_date": estimated})
    orders.to_csv(SAMPLE_DIR / CSV_FILES["orders"], index=False)

 
    n_items = rng.choice([1, 2, 3], n_orders, p=[.88, .09, .03])
    rows = []
    for oid, k, ss in zip(orders["order_id"], n_items, seller_state):
        pool = sellers.index[sellers["seller_state"] == ss]
        sid = sellers.loc[rng.choice(pool) if len(pool) else rng.integers(0, n_sell), "seller_id"]
        for j in range(k):
            price = round(float(rng.lognormal(4.3, 0.8)), 2)
            rows.append((oid, j + 1, products["product_id"].iloc[rng.integers(0, n_prod)], sid,
                         "2017-01-01 00:00:00", price, round(price * rng.uniform(0.08, 0.35), 2)))
    items = pd.DataFrame(rows, columns=["order_id", "order_item_id", "product_id", "seller_id",
                                        "shipping_limit_date", "price", "freight_value"])
    items.to_csv(SAMPLE_DIR / CSV_FILES["order_items"], index=False)


    tot = items.groupby("order_id")[["price", "freight_value"]].sum().sum(axis=1)
    pay = []
    for oid, v in tot.items():
        if rng.random() < 0.06:
            pay += [(oid, 1, "voucher", 1, round(v * .3, 2)), (oid, 2, "credit_card", 3, round(v * .7, 2))]
        else:
            pay.append((oid, 1, rng.choice(["credit_card", "boleto", "debit_card"], p=[.76, .2, .04]),
                        int(rng.integers(1, 8)), round(v, 2)))
    pd.DataFrame(pay, columns=["order_id", "payment_sequential", "payment_type",
                               "payment_installments", "payment_value"]) \
        .to_csv(SAMPLE_DIR / CSV_FILES["order_payments"], index=False)

   
    late = (delivered.dt.normalize() > estimated).fillna(False).values
    score = np.empty(n_orders, dtype=int)
    for i in range(n_orders):
        dist = [.40, .12, .13, .20, .15] if late[i] else [.04, .03, .08, .22, .63]
        score[i] = rng.choice([1, 2, 3, 4, 5], p=dist)
    has_review = rng.random(n_orders) < 0.97
    rev = pd.DataFrame({
        "review_id": [f"r{i:06d}" for i in range(n_orders)],
        "order_id": orders["order_id"], "review_score": score,
        "review_comment_title": None, "review_comment_message": None,
        "review_creation_date": delivered.fillna(purchase),
        "review_answer_timestamp": delivered.fillna(purchase) + pd.Timedelta(days=1)})[has_review]
    dup = rev.sample(frac=0.02, random_state=1).copy()       
    dup["review_id"] = dup["review_id"] + "_dup"
    dup["review_score"] = rng.integers(1, 6, len(dup))
    dup["review_answer_timestamp"] += pd.Timedelta(days=2)
    pd.concat([rev, dup]).to_csv(SAMPLE_DIR / CSV_FILES["order_reviews"], index=False)

    pd.DataFrame({"geolocation_zip_code_prefix": [1000], "geolocation_lat": [-23.5],
                  "geolocation_lng": [-46.6], "geolocation_city": ["sao paulo"],
                  "geolocation_state": ["SP"]}).to_csv(SAMPLE_DIR / CSV_FILES["geolocation"], index=False)
    print(f"Synthetic sample written to {SAMPLE_DIR} ({n_orders} orders). FOR TESTING ONLY.")


if __name__ == "__main__":
    generate()
