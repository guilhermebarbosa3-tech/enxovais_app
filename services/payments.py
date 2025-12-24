from core.db import get_conn, exec_query, is_postgres_conn, now_iso

def create_payment_batch(order_ids: list[int]) -> int:
    conn = get_conn()
    is_pg = is_postgres_conn(conn)

    # soma custos (usar exec_query para compatibilidade de placeholders)
    qmarks = ",".join(["?"]*len(order_ids))
    r = exec_query(f"SELECT SUM(cost) AS total FROM finance_entries WHERE order_id IN ({qmarks}) AND settled=0", order_ids).fetchone()
    total = r['total'] if (isinstance(r, dict) or hasattr(r, 'keys')) else (r[0] if r else 0.0)
    total = total or 0.0

    # Inserir batch e recuperar id: usar RETURNING em Postgres, lastrowid em SQLite
    if is_pg:
        cur = exec_query("INSERT INTO payment_batches(total, created_at) VALUES (%s, %s) RETURNING id", (total, now_iso()))
        batch_id = cur.fetchone()['id']
    else:
        cur = exec_query("INSERT INTO payment_batches(total, created_at) VALUES (?, ?)", (total, now_iso()), commit=True)
        # sqlite cursor returned by exec_query supports lastrowid
        try:
            batch_id = cur.lastrowid
        except Exception:
            batch_id = None

    # Atualizar entradas
    if is_pg:
        # Postgres placeholder already handled by exec_query conversion when using ?; but we'll use %s explicitly
        qmarks = ",".join(["%s"]*len(order_ids))
        params = [batch_id, *order_ids]
        exec_query(f"UPDATE finance_entries SET settled=1, batch_id=%s WHERE order_id IN ({qmarks}) AND settled=0", params, commit=True)
    else:
        qmarks = ",".join(["?"]*len(order_ids))
        exec_query(f"UPDATE finance_entries SET settled=1, batch_id=? WHERE order_id IN ({qmarks}) AND settled=0", [batch_id, *order_ids], commit=True)

    return batch_id
