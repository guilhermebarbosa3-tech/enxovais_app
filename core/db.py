import json, os, datetime
from typing import Any, Dict

# Detectar se estamos em produção (PostgreSQL) ou desenvolvimento (SQLite)
DATABASE_URL = os.environ.get('DATABASE_URL')

# Importações condicionais
if DATABASE_URL:
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
        HAS_PSYCOPG = True
    except ImportError:
        HAS_PSYCOPG = False
        raise ImportError("psycopg2-binary não instalado. Instale com: pip install psycopg2-binary")
else:
    HAS_PSYCOPG = False
    import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "exonvais.db")
DB_PATH = os.path.abspath(DB_PATH)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  address TEXT,
  cpf TEXT,
  phone TEXT,
  status TEXT DEFAULT 'ADIMPLENTE'
);

CREATE TABLE IF NOT EXISTS product_catalog (
  id SERIAL PRIMARY KEY,
  category TEXT NOT NULL,
  type TEXT NOT NULL,
  product TEXT NOT NULL,
  measure_based INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY,
  client_id INTEGER NOT NULL,
  category TEXT NOT NULL,
  type TEXT NOT NULL,
  product TEXT NOT NULL,
  price_cost REAL NOT NULL,
  price_sale REAL NOT NULL,
  notes_struct TEXT DEFAULT '{}',
  notes_free TEXT DEFAULT '',
  photos TEXT DEFAULT '[]',
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS shipments (
  id SERIAL PRIMARY KEY,
  order_id INTEGER NOT NULL,
  medium TEXT,
  when_ts TEXT NOT NULL,
  document_path TEXT,
  FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS nonconformities (
  id SERIAL PRIMARY KEY,
  order_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  description TEXT,
  photos TEXT DEFAULT '[]',
  count INTEGER DEFAULT 1,
  created_at TEXT NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS finance_entries (
  id SERIAL PRIMARY KEY,
  order_id INTEGER NOT NULL,
  cost REAL NOT NULL,
  sale REAL NOT NULL,
  margin REAL NOT NULL,
  settled INTEGER DEFAULT 0,
  batch_id INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS payment_batches (
  id SERIAL PRIMARY KEY,
  total REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id SERIAL PRIMARY KEY,
  entity TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  field TEXT,
  before TEXT,
  after TEXT,
  user TEXT,
  ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

_conn = None

def get_conn():
    global _conn
    if _conn is None:
        if HAS_PSYCOPG:
            # PostgreSQL
            _conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            # SQLite
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
    return _conn


def init_db():
    conn = get_conn()
    if HAS_PSYCOPG:
        # PostgreSQL
        conn.execute(SCHEMA_SQL)
        conn.commit()
    else:
        # SQLite
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False)


def from_json(txt, default):
    try:
        return json.loads(txt) if txt else default
    except Exception:
        return default


def audit(entity: str, entity_id: int, action: str, field: str | None = None, before: Any = None, after: Any = None, user: str = "system"):
    conn = get_conn()
    before_json = to_json(before) if before is not None else None
    after_json = to_json(after) if after is not None else None
    conn.execute(
        "INSERT INTO audit_log(entity, entity_id, action, field, before, after, user, ts) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)" if HAS_PSYCOPG else
        "INSERT INTO audit_log(entity, entity_id, action, field, before, after, user, ts) VALUES (?,?,?,?,?,?,?,?)",
        (entity, entity_id, action, field, before_json, after_json, user, now_iso())
    )
    conn.commit()


def load_config(key: str, default: Any):
    """Carrega configuração do banco (centralizado)"""
    conn = get_conn()
    if HAS_PSYCOPG:
        # PostgreSQL
        conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        cur = conn.execute("SELECT value FROM config WHERE key=%s", (key,))
    else:
        # SQLite
        conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        cur = conn.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    if row:
        return from_json(row['value'] if HAS_PSYCOPG else row[0], default)
    else:
        # Se não existe, salva o padrão
        save_config(key, default)
        return default


def save_config(key: str, value: Any):
    """Salva configuração no banco (centralizado)"""
    conn = get_conn()
    if HAS_PSYCOPG:
        # PostgreSQL - usar ON CONFLICT
        conn.execute("""
            INSERT INTO config(key, value) VALUES (%s,%s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, to_json(value)))
    else:
        # SQLite
        conn.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?,?)", (key, to_json(value)))
    conn.commit()
