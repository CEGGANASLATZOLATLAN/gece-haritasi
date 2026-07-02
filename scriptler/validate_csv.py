"""Aylık ham CSV dosyasını analiz öncesi doğrular.

Kullanım:
    python scriptler/validate_csv.py veri/ham/hourly_transportation_202410.csv

Kontroller:
- Kolon şeması beklenen 13 kolonla uyuşuyor mu (aylar arası şema kayması tespiti)
- Ayın tüm günleri var mı, her günün 24 saati dolu mu
- Tam gün sayısı (analize uygunluk kararı için)
- Kritik kolonlarda NULL oranları

Çıkış kodu: 0 = TAM, 1 = EKSİK/SORUNLU (pipeline'da zincirlemek için).
"""

import sys
import calendar

import duckdb

BEKLENEN_KOLONLAR = [
    "transition_date", "transition_hour", "transport_type_id", "road_type",
    "line", "transfer_type", "number_of_passage", "number_of_passenger",
    "product_kind", "transaction_type_desc", "town", "line_name",
    "station_poi_desc_cd",
]

# Gerçek bir gün ~550 bin satırdır, bozuk dosyalardaki "kırıntı" günler ~1000 satır.
# Saat bazlı eşik işe yaramaz: gerçek gece saatleri (01-04, ~400 satır) kırıntılarla
# aynı büyüklükte. Ayrım gün toplamından yapılır.
MIN_SATIR_PER_GUN = 100_000


def validate(csv_path: str) -> bool:
    print(f"\n=== {csv_path} ===")
    sorun = False

    kolonlar = [
        r[0] for r in duckdb.sql(f"DESCRIBE SELECT * FROM '{csv_path}'").fetchall()
    ]
    if kolonlar != BEKLENEN_KOLONLAR:
        sorun = True
        print("[SORUN] Şema beklenenden farklı!")
        print(f"  beklenen: {BEKLENEN_KOLONLAR}")
        print(f"  gelen   : {kolonlar}")
    else:
        print("[OK] Şema: 13 kolon beklendiği gibi")

    ozet = duckdb.sql(f"""
        SELECT COUNT(*),
               MIN(transition_date), MAX(transition_date),
               COUNT(DISTINCT transition_date)
        FROM '{csv_path}'
    """).fetchone()
    satir, ilk_gun, son_gun, gun_sayisi = ozet
    yil, ay = ilk_gun.year, ilk_gun.month
    ay_gun = calendar.monthrange(yil, ay)[1]
    print(f"Satır: {satir:,} | Kapsam: {ilk_gun} → {son_gun} "
          f"({gun_sayisi}/{ay_gun} gün)")

    if gun_sayisi < ay_gun:
        sorun = True
        print(f"[SORUN] Ayın {ay_gun - gun_sayisi} günü hiç yok")

    # Tam gün = 24 farklı saat VE gün toplamı eşiğin üstünde
    gunler = duckdb.sql(f"""
        SELECT transition_date,
               COUNT(DISTINCT transition_hour) AS saat,
               COUNT(*) AS satir
        FROM '{csv_path}'
        GROUP BY 1 ORDER BY 1
    """).fetchall()

    tam_gunler = [str(g) for g, saat, satir in gunler
                  if saat == 24 and satir >= MIN_SATIR_PER_GUN]
    eksik_gunler = [(str(g), saat, satir) for g, saat, satir in gunler
                    if saat < 24 or satir < MIN_SATIR_PER_GUN]

    print(f"Tam günler ({len(tam_gunler)}/{ay_gun}): {', '.join(tam_gunler) or '-'}")
    if eksik_gunler:
        sorun = True
        print(f"[SORUN] Eksik/kırıntı {len(eksik_gunler)} gün:")
        for g, saat, satir in eksik_gunler:
            print(f"  {g}: {saat}/24 saat, {satir:,} satır")

    nuller = duckdb.sql(f"""
        SELECT
            COUNT(*) FILTER (town IS NULL OR TRIM(town) = '') AS town_bos,
            COUNT(*) FILTER (line_name IS NULL OR TRIM(line_name) = '') AS hat_bos,
            COUNT(*) FILTER (number_of_passenger IS NULL) AS yolcu_bos,
            COUNT(*) AS toplam
        FROM '{csv_path}'
    """).fetchone()
    town_bos, hat_bos, yolcu_bos, toplam = nuller
    print(f"NULL oranları: town %{100 * town_bos / toplam:.1f}, "
          f"line_name %{100 * hat_bos / toplam:.1f}, "
          f"passenger %{100 * yolcu_bos / toplam:.1f}")
    if yolcu_bos:
        sorun = True
        print(f"[SORUN] {yolcu_bos:,} satırda yolcu sayısı NULL")

    print("SONUÇ:", "EKSİK/SORUNLU ⚠️" if sorun else "TAM ✅")
    return not sorun


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sonuclar = [validate(p) for p in sys.argv[1:]]
    sys.exit(0 if all(sonuclar) else 1)
