import json, os, datetime
from typing import Any, Dict, Union

# Versão do schema para forçar redeploy limpo
__schema_version__ = "1.1.0"

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
_db_initialized = False

# Schema para PostgreSQL
SCHEMA_SQL_PG = """
CREATE TABLE IF NOT EXISTS clients (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  address TEXT,
  cpf TEXT,
  phone TEXT,
  status TEXT DEFAULT 'ADIMPLENTE',
  is_active INTEGER DEFAULT 1
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
  username TEXT,
  ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS stock_items (
  id SERIAL PRIMARY KEY,
  category TEXT NOT NULL,
  type TEXT NOT NULL,
  product TEXT NOT NULL,
  price_cost REAL NOT NULL,
  price_sale REAL NOT NULL,
  notes_struct TEXT DEFAULT '{}',
  notes_free TEXT DEFAULT '',
  photos TEXT DEFAULT '[]',
  quantity INTEGER DEFAULT 1,
  owner_client_id INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(owner_client_id) REFERENCES clients(id)
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
  status TEXT DEFAULT 'ADIMPLENTE',
  is_active INTEGER DEFAULT 1
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
  username TEXT,
  ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS stock_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL,
  type TEXT NOT NULL,
  product TEXT NOT NULL,
  price_cost REAL NOT NULL,
  price_sale REAL NOT NULL,
  notes_struct TEXT DEFAULT '{}',
  notes_free TEXT DEFAULT '',
  photos TEXT DEFAULT '[]',
  quantity INTEGER DEFAULT 1,
  owner_client_id INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(owner_client_id) REFERENCES clients(id)
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
    global _db_initialized
    if _db_initialized:
        return  # Já inicializado, evita rodar múltiplas vezes
    
    print("🚀 INICIANDO init_db()")
    conn = get_conn()
    if is_postgres_conn(conn):
        # PostgreSQL - executar cada statement com SAVEPOINT individual
        try:
            cursor = conn.cursor()
            statements = [stmt.strip() for stmt in SCHEMA_SQL_PG.split(';') if stmt.strip()]
            for i, stmt in enumerate(statements):
                if not stmt:
                    continue
                sp = f"sp_{i}"
                try:
                    cursor.execute(f"SAVEPOINT {sp}")
                    cursor.execute(stmt)
                    cursor.execute(f"RELEASE SAVEPOINT {sp}")
                except Exception as stmt_error:
                    cursor.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                    cursor.execute(f"RELEASE SAVEPOINT {sp}")
                    err_msg = str(stmt_error).lower()
                    if "already exists" not in err_msg:
                        print(f"⚠️ Aviso ao executar statement PG: {stmt_error}")
            conn.commit()
            cursor.close()
            print("✅ Schema PostgreSQL criado/atualizado")
        except Exception as e:
            print(f"❌ Erro ao executar schema PostgreSQL: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
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
    
    # Executar migrações automáticas
    _run_migrations()
    
    _db_initialized = True
    print("✅ FINALIZADO init_db()")


def _run_migrations():
    """Executa migrações pendentes automaticamente (usa SQL direto, sem exec_query)"""
    print("📦 Verificando migrações...")
    conn = get_conn()
    is_pg = is_postgres_conn(conn)
    
    try:
        # Migração 001: Adicionar is_active aos clientes
        if is_pg:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'clients' AND column_name = 'is_active'
            """)
            result = cursor.fetchone()
            has_is_active = result is not None
            cursor.close()
        else:
            cols = conn.execute("PRAGMA table_info(clients)").fetchall()
            # PRAGMA retorna: cid, name, type, notnull, dflt_value, pk
            # Usar índice numérico [1] para o nome da coluna (mais robusto)
            column_names = []
            for col in cols:
                try:
                    # Tentar acesso por chave primeiro, depois por índice
                    col_name = col['name'] if hasattr(col, 'keys') else col[1]
                    column_names.append(col_name)
                except (KeyError, IndexError, TypeError):
                    continue
            has_is_active = 'is_active' in column_names
        
        if not has_is_active:
            print("📝 Migração 001: Adicionando coluna is_active...")
            if is_pg:
                cursor = conn.cursor()
                cursor.execute("ALTER TABLE clients ADD COLUMN is_active INTEGER DEFAULT 1")
                cursor.execute("UPDATE clients SET is_active = 1 WHERE is_active IS NULL")
                # Criar índice único agora que a coluna existe
                try:
                    cursor.execute(
                        "CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_name_unique "
                        "ON clients (LOWER(TRIM(name))) WHERE is_active = 1"
                    )
                except Exception as idx_err:
                    print(f"⚠️ Índice de unicidade não criado (não crítico): {idx_err}")
                conn.commit()
                cursor.close()
            else:
                conn.execute("ALTER TABLE clients ADD COLUMN is_active INTEGER DEFAULT 1")
                conn.execute("UPDATE clients SET is_active = 1 WHERE is_active IS NULL")
                conn.commit()
            print("✅ Migração 001 concluída!")
        
        print("✅ Todas as migrações verificadas")
    except Exception as e:
        print(f"⚠️ Erro ao verificar migrações: {e}")


def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False)


def from_json(txt, default):
    try:
        return json.loads(txt) if txt else default
    except Exception:
        return default


def audit(entity: str, entity_id: int, action: str, field: str | None = None, before: Any = None, after: Any = None, username: str = "system"):
    conn = get_conn()
    is_pg = is_postgres_conn(conn)
    before_json = to_json(before) if before is not None else None
    after_json = to_json(after) if after is not None else None
    
    if is_pg:
        cursor = conn.cursor()
        cursor.execute(
          "INSERT INTO audit_log(entity, entity_id, action, field, before, after, username, ts) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
          (entity, entity_id, action, field, before_json, after_json, username, now_iso())
        )
        conn.commit()
        cursor.close()
    else:
        conn.execute(  # type: ignore
          "INSERT INTO audit_log(entity, entity_id, action, field, before, after, username, ts) VALUES (?,?,?,?,?,?,?,?)",
          (entity, entity_id, action, field, before_json, after_json, username, now_iso())
        )
        conn.commit()  # type: ignore


def load_config(key: str, default: Any):
    """Carrega configuração do banco (centralizado)"""
    conn = get_conn()
    is_pg = is_postgres_conn(conn)

    if is_pg:
        # PostgreSQL
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("SELECT value FROM config WHERE key=%s", (key,))
        row = cursor.fetchone()
        cursor.close()
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
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO config(key, value) VALUES (%s,%s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, to_json(value)))
        conn.commit()
        cursor.close()
    else:
        # SQLite
        conn.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?,?)", (key, to_json(value)))  # type: ignore
        conn.commit()  # type: ignore


def exec_query(sql: str, params: tuple | list | None = None, commit: bool = False):
  """Execute uma query abstrata que funciona em SQLite e PostgreSQL.

  - Em PostgreSQL usa `cursor.execute()` e converte placeholders `?` → `%s`.
  - Em SQLite usa `conn.execute()` com `?`.
  Retorna o cursor/result proxy (tem `fetchall()` / `fetchone()`).
  """
  conn = get_conn()
  is_pg = is_postgres_conn(conn)
  params = tuple(params or ())

  if is_pg:
    cur = conn.cursor()
    if "?" in sql:
      sql = sql.replace("?", "%s")
    try:
      cur.execute(sql, params)
      if commit:
        conn.commit()
      return cur
    except Exception:
      # Se ocorrer erro, garante rollback para sair do estado de transação falho
      try:
        conn.rollback()
      except Exception:
        pass
      cur.close()
      raise

  # SQLite path
  try:
    cur = conn.execute(sql, params)  # type: ignore
    if commit:
      conn.commit()  # type: ignore
    return cur
  except Exception:
    try:
      conn.rollback()
    except Exception:
      pass
    raise
