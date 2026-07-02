"""DuckDB bağlantı yardımcıları.

Kullanım:
    from kaynak.db import baglan
    con = baglan()
    con.sql("SELECT COUNT(*) FROM yolculuk").show()

`yolculuk` view'ı tüm 2023 Parquet dosyalarını kapsar ve türetilmiş zaman
kolonlarını hazır verir (ay, haftanın günü, gün tipi).
"""

from pathlib import Path

import duckdb

PROJE_KOKU = Path(__file__).resolve().parent.parent
PARQUET_GLOB = str(PROJE_KOKU / "veri" / "islenmis" / "hourly_2023*.parquet")

# Tek noktadan yönetilen view tanımı: SQL dosyaları da bu view'ı kullanır
YOLCULUK_VIEW = f"""
CREATE OR REPLACE VIEW yolculuk AS
SELECT
    *,
    MONTH(transition_date)                          AS ay,
    ISODOW(transition_date)                         AS haftanin_gunu,  -- 1=Pzt..7=Paz
    CASE WHEN ISODOW(transition_date) <= 5
         THEN 'hafta içi' ELSE 'hafta sonu' END     AS gun_tipi
FROM '{PARQUET_GLOB}'
"""


def baglan(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """`yolculuk` view'ı hazır bir DuckDB bağlantısı döndürür."""
    con = duckdb.connect(db_path) if db_path else duckdb.connect()
    con.sql(YOLCULUK_VIEW)
    return con


def sql_dosyasi_calistir(con: duckdb.DuckDBPyConnection, sql_path: str | Path):
    """sql/ altındaki bir sorgu dosyasını çalıştırıp sonucu döndürür."""
    sorgu = Path(sql_path).read_text(encoding="utf-8")
    return con.sql(sorgu)
