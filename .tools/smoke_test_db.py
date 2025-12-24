r"""
Smoke test para DB usando a variável de ambiente DATABASE_URL.
Usage:
    $env:DATABASE_URL = 'postgresql://user:pass@host:5432/db'
    python .\.tools\smoke_test_db.py

O script tenta usar psycopg2 para Postgres. Se não existir, indica instalação.
"""
import os
import sys

def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        print('DATABASE_URL não está definida. Ex.: postgresql://user:pass@host:5432/db')
        sys.exit(1)

    if url.startswith('postgres'):
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            print('psycopg2 não instalado no ambiente. Instale com: python -m pip install psycopg2-binary')
            sys.exit(2)
        try:
            conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) AS c FROM orders')
            r = cur.fetchone()
            # r can be a dict (RealDictCursor) or a tuple; handle both
            if r:
                if isinstance(r, dict):
                    print('orders:', r.get('c', 0))
                else:
                    # sequence/tuple-like
                    try:
                        print('orders:', r[0])
                    except Exception:
                        print('orders:', 0)
            else:
                print('orders:', 0)

            cur.execute('SELECT COUNT(*) AS c FROM audit_log')
            r = cur.fetchone()
            if r:
                if isinstance(r, dict):
                    print('audit_log:', r.get('c', 0))
                else:
                    try:
                        print('audit_log:', r[0])
                    except Exception:
                        print('audit_log:', 0)
            else:
                print('audit_log:', 0)
            conn.close()
        except Exception as e:
            print('Erro ao conectar/consultar Postgres:', e)
            sys.exit(3)
    elif url.startswith('sqlite'):
        import sqlite3
        # suportar sqlite:///path/to/db
        path = url.replace('sqlite:///', '')
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM orders')
            r = cur.fetchone()
            if r:
                try:
                    print('orders:', r[0])
                except Exception:
                    print('orders:', 0)
            else:
                print('orders:', 0)

            cur.execute('SELECT COUNT(*) FROM audit_log')
            r = cur.fetchone()
            if r:
                try:
                    print('audit_log:', r[0])
                except Exception:
                    print('audit_log:', 0)
            else:
                print('audit_log:', 0)
            conn.close()
        except Exception as e:
            print('Erro ao conectar/consultar SQLite:', e)
            sys.exit(4)
    else:
        print('DATABASE_URL com esquema não suportado pelo script:', url.split(':',1)[0])
        sys.exit(5)

if __name__ == '__main__':
    main()
