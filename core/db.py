import sqlite3, json, os, datetime
from typing import Any, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "exonvais.db")
DB_PATH = os.path.abspath(DB_PATH)

SCHEMA_SQL = r"""
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  address TEXT,
  cpf TEXT,
  phone TEXT,
  status TEXT DEFAULT 'ADIMPLENTE'
);

CREATE TABLE IF NOT EXISTS product_catalog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL,
  type TEXT NOT NULL,
  product TEXT NOT NULL,
  measure_based INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  medium TEXT,
  when_ts TEXT NOT NULL,
  document_path TEXT,
  FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS nonconformities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  description TEXT,
  photos TEXT DEFAULT '[]',
  count INTEGER DEFAULT 1,
  created_at TEXT NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS finance_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  total REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  field TEXT,
  before TEXT,
  after TEXT,
  user TEXT,
  ts TEXT NOT NULL
);
"""

_conn = None

def get_conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    return _conn


def init_db():
    conn = get_conn()
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
        "INSERT INTO audit_log(entity, entity_id, action, field, before, after, user, ts) VALUES (?,?,?,?,?,?,?,?)",
        (entity, entity_id, action, field, before_json, after_json, user, now_iso())
    )
    conn.commit()


def load_config(key: str, default: Any):
    """Carrega configuração do banco (centralizado)"""
    conn = get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    cur = conn.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    if row:
        return from_json(row[0], default)
    else:
        # Se não existe, salva o padrão
        save_config(key, default)
        return default


def save_config(key: str, value: Any):
    """Salva configuração no banco (centralizado)"""
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?,?)", (key, to_json(value)))
    conn.commit()
