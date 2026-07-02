"""Ham aylık CSV'leri temiz Parquet'e çevirir (CSV → veri/islenmis/).

Kullanım:
    python kaynak/ingest.py                # veri/ham/ altındaki tüm ayları işler
    python kaynak/ingest.py 202301 202302  # sadece verilen ayları işler

Temizlik kuralları:
- transition_hour: "00".."23" string → TINYINT
- Boş string'ler NULL'a çevrilir (town, line_name, station_poi_desc_cd, line)
- Kolon adları kaynaktakiyle aynı bırakılır (izlenebilirlik; bkz. veri/VERI_SOZLUGU.md)
- Ham veri ASLA değiştirilmez; çıktı ZSTD sıkıştırmalı Parquet

Not: Zaten dönüştürülmüş aylar atlanır (çıktı dosyası varsa). Yeniden üretmek
için önce veri/islenmis/ altındaki ilgili parquet'i sil.
"""

import sys
from pathlib import Path

import duckdb

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW = PROJE_KOKU / "veri" / "ham"
PROCESSED = PROJE_KOKU / "veri" / "islenmis"


def donustur(csv_path: Path, parquet_path: Path) -> None:
    duckdb.sql(f"""
        COPY (
            SELECT
                transition_date,
                CAST(transition_hour AS TINYINT)          AS transition_hour,
                CAST(transport_type_id AS TINYINT)        AS transport_type_id,
                road_type,
                NULLIF(TRIM(line), '')                    AS line,
                transfer_type,
                CAST(number_of_passage AS INTEGER)        AS number_of_passage,
                CAST(number_of_passenger AS INTEGER)      AS number_of_passenger,
                product_kind,
                transaction_type_desc,
                NULLIF(TRIM(town), '')                    AS town,
                NULLIF(TRIM(line_name), '')               AS line_name,
                NULLIF(TRIM(station_poi_desc_cd), '')     AS station_poi_desc_cd
            FROM read_csv('{csv_path}', header=true)
        ) TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)


def main() -> None:
    aylar = sys.argv[1:]  # boşsa hepsi
    csvler = sorted(RAW.glob("hourly_transportation_*.csv"))
    if aylar:
        csvler = [p for p in csvler if p.stem.split("_")[-1] in aylar]
    if not csvler:
        sys.exit(f"veri/ham/ altında işlenecek CSV yok (filtre: {aylar or 'yok'})")

    for csv_path in csvler:
        ay = csv_path.stem.split("_")[-1]
        parquet_path = PROCESSED / f"hourly_{ay}.parquet"
        if parquet_path.exists():
            print(f"{ay}: zaten var, atlandı")
            continue
        donustur(csv_path, parquet_path)
        mb_in = csv_path.stat().st_size / 1e6
        mb_out = parquet_path.stat().st_size / 1e6
        print(f"{ay}: {mb_in:,.0f} MB CSV → {mb_out:,.0f} MB Parquet")


if __name__ == "__main__":
    main()
