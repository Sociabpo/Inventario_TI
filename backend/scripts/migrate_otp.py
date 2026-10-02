r"""
Migración: verificación OTP para la firma digital.
  - firma_tokens: columna otp_verificado
  - tabla otp_tokens

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_otp.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

STATEMENTS = [
    ("firma_tokens.otp_verificado",
     "ALTER TABLE firma_tokens ADD COLUMN otp_verificado BOOLEAN NOT NULL DEFAULT FALSE"),
    ("tabla otp_tokens",
     """CREATE TABLE otp_tokens (
            id VARCHAR(36) PRIMARY KEY,
            firma_token_id VARCHAR(36) NOT NULL,
            codigo VARCHAR(6) NOT NULL,
            usado BOOLEAN DEFAULT FALSE,
            verificado BOOLEAN DEFAULT FALSE,
            intentos_fallidos INTEGER DEFAULT 0,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT NOW(),
            FOREIGN KEY (firma_token_id) REFERENCES firma_tokens(id)
        )"""),
]

with engine.connect() as conn:
    for nombre, ddl in STATEMENTS:
        try:
            conn.execute(text(ddl))
            conn.commit()
            print(f"[+] Aplicado: {nombre}")
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("duplicate column", "already exists", "1050", "1060")):
                print(f"[=] Ya existe: {nombre}")
            else:
                print(f"[ERROR] {nombre}: {e}")
                sys.exit(1)

    print("\nMigración OTP completada.")
