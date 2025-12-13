from core.db import get_conn

def create_payment_batch(order_ids: list[int]) -> int:
    conn = get_conn()
    cur = conn.cursor()
    # soma custos
    qmarks = ",".join(["?"]*len(order_ids))
    cur.execute(f"SELECT SUM(cost) FROM finance_entries WHERE order_id IN ({qmarks}) AND settled=0", order_ids)
    total = cur.fetchone()[0] or 0.0
    cur.execute("INSERT INTO payment_batches(total, created_at) VALUES (?, datetime('now'))", (total,))
    batch_id = cur.lastrowid
    cur.execute(f"UPDATE finance_entries SET settled=1, batch_id=? WHERE order_id IN ({qmarks}) AND settled=0", [batch_id, *order_ids])
    conn.commit()
    return batch_id
