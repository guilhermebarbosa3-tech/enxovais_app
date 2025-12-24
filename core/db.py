import json, os, datetime
from typing import Any, Dict, Union

# Detectar se estamos em produção (PostgreSQL) ou desenvolvimento (SQLite)
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"🔍 DATABASE_URL presente: {bool(DATABASE_URL)}")
if DATABASE_URL:
    print(f"🔍 DATABASE_URL: {DATABASE_URL[:50]}...")  # Log parcial por segurança

# Importações condicionais - lazy loading
HAS_PSYCOPG = False
if DATABASE_URL:
    try:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
        HAS_PSYCOPG = True
        print("✅ psycopg2 importado com sucesso")
    except ImportError as e:
        # PostgreSQL não disponível, usar SQLite
        HAS_PSYCOPG = False
        print(f"⚠️ PostgreSQL não disponível: {e}")
else:
    print("ℹ️ Sem DATABASE_URL, usando SQLite")
    HAS_PSYCOPG = False

import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "exonvais.db")
DB_PATH = os.path.abspath(DB_PATH)

# Conexão global (singleton)
_conn = None

# Schema para PostgreSQL
SCHEMA_SQL_PG = """
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

# Schema para SQLite
SCHEMA_SQL_SQLITE = """
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

CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

def get_conn() -> Any:
    global _conn
    if _conn is None:
        if HAS_PSYCOPG and DATABASE_URL:
            try:
                # PostgreSQL
                _conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
                print("✅ BACKEND ESCOLHIDO: PostgreSQL (produção)")
            except Exception as e:
                print(f"⚠️ Falha na conexão PostgreSQL: {e}")
                print("🔄 Fazendo fallback para SQLite")
                # Fallback para SQLite se PostgreSQL falhar
                _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                _conn.row_factory = sqlite3.Row
                print("✅ BACKEND ESCOLHIDO: SQLite (fallback)")
        else:
            # SQLite (desenvolvimento)
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            print("✅ BACKEND ESCOLHIDO: SQLite (desenvolvimento)")
    return _conn


def is_postgres_conn(conn) -> bool:
    """Verifica se a conexão é PostgreSQL ou SQLite"""
    # Verifica se é uma conexão psycopg2 (PostgreSQL)
    return str(type(conn)).startswith("<class 'psycopg2")


def init_db():
    print("🚀 INICIANDO init_db()")
    conn = get_conn()
    if is_postgres_conn(conn):
        # PostgreSQL - executar cada statement separadamente
        try:
            # Dividir o schema em statements individuais
            statements = [stmt.strip() for stmt in SCHEMA_SQL_PG.split(';') if stmt.strip()]
            for stmt in statements:
                if stmt:  # Ignorar statements vazios
                    conn.execute(stmt)  # type: ignore
            conn.commit()  # type: ignore
            print("✅ Schema PostgreSQL criado/atualizado")
            print("✅ FINALIZADO init_db()")
        except Exception as e:
            print(f"❌ Erro ao executar schema PostgreSQL: {e}")
            # Fallback para SQLite se schema PostgreSQL falhar
            print("🔄 Fazendo fallback para SQLite")
            sqlite_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            sqlite_conn.row_factory = sqlite3.Row
            sqlite_conn.executescript(SCHEMA_SQL_SQLITE)
            sqlite_conn.commit()
            global _conn
            _conn = sqlite_conn
    else:
        # SQLite
        conn.executescript(SCHEMA_SQL_SQLITE)  # type: ignore
        conn.commit()
        print("✅ Schema SQLite criado/atualizado")
    print("✅ FINALIZADO init_db()")


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
    is_pg = is_postgres_conn(conn)
    before_json = to_json(before) if before is not None else None
    after_json = to_json(after) if after is not None else None
    conn.execute(  # type: ignore
        "INSERT INTO audit_log(entity, entity_id, action, field, before, after, user, ts) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)" if is_pg else
        "INSERT INTO audit_log(entity, entity_id, action, field, before, after, user, ts) VALUES (?,?,?,?,?,?,?,?)",
        (entity, entity_id, action, field, before_json, after_json, user, now_iso())
    )
    conn.commit()  # type: ignore


def load_config(key: str, default: Any):
    """Carrega configuração do banco (centralizado)"""
    conn = get_conn()
    is_pg = is_postgres_conn(conn)

    if is_pg:
        # PostgreSQL
        conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")  # type: ignore
        cur = conn.execute("SELECT value FROM config WHERE key=%s", (key,))  # type: ignore
    else:
        # SQLite
        conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")  # type: ignore
        cur = conn.execute("SELECT value FROM config WHERE key=?", (key,))  # type: ignore

    row = cur.fetchone()
    if row:
        return from_json(row['value'] if is_pg else row[0], default)
    else:
        # Se não existe, salva o padrão
        save_config(key, default)
        return default


def save_config(key: str, value: Any):
    """Salva configuração no banco (centralizado)"""
    conn = get_conn()
    is_pg = is_postgres_conn(conn)
    if is_pg:
        # PostgreSQL - usar ON CONFLICT
        conn.execute("""  # type: ignore[attr-defined]
            INSERT INTO config(key, value) VALUES (%s,%s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, to_json(value)))
    else:
        # SQLite
        conn.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?,?)", (key, to_json(value)))  # type: ignore
    conn.commit()  # type: ignore  # type: ignore
