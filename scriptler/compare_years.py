"""Yıllar arası karşılaştırma grafikleri.

Kullanım (proje kökünden):
    python scriptler/compare_years.py

veri/islenmis/ altında hangi yıllar varsa hepsini kıyaslar (kısmi yıllar
dahil — kısmi yıl uyarısı grafiğe not düşülür).
Çıktılar: ciktilar/grafikler/karsilastirma/
"""

import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOKU))

import matplotlib.pyplot as plt
import seaborn as sns

from kaynak.db import PROCESSED, baglan
from kaynak.viz import FIGURES, RENKLER, stil

CIKTI = FIGURES / "karsilastirma"
KAYNAK = "Kaynak: İBB Açık Veri (Saatlik Toplu Ulaşım Veri Seti)"
YIL_RENKLERI = ["#8d99ae", "#1f6f8b", "#e4572e", "#c1121f"]  # eskiden yeniye


def kaydet(fig, ad):
    fig.text(0.99, -0.01, KAYNAK, ha="right", va="top", fontsize=8, color="gray")
    CIKTI.mkdir(parents=True, exist_ok=True)
    yol = CIKTI / f"{ad}.png"
    fig.savefig(yol, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"kaydedildi: {yol.relative_to(PROJE_KOKU)}")


def k1_aylik_hacim(con, yillar):
    df = con.sql("""
        WITH gunluk AS (
            SELECT yil, ay, transition_date, SUM(number_of_passenger) AS yolcu
            FROM yolculuk GROUP BY 1, 2, 3
        )
        SELECT yil, ay, AVG(yolcu) AS ort_gunluk
        FROM gunluk GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    fig, ax = plt.subplots()
    for renk, (yil, grup) in zip(YIL_RENKLERI, df.groupby("yil")):
        ax.plot(grup["ay"], grup["ort_gunluk"] / 1e6, marker="o",
                color=renk, linewidth=2.2, label=str(yil))
    ax.set_title("İstanbul yıldan yıla nasıl kalabalıklaştı?")
    ax.set_xlabel("Ay")
    ax.set_ylabel("Ortalama günlük yolcu (milyon)")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Oca", "Şub", "Mar", "Nis", "May", "Haz",
                        "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"])
    ax.legend(title=None)
    kaydet(fig, "k1_aylik_hacim")


def k2_saatlik_profil(con, yillar):
    df = con.sql("""
        WITH gunluk AS (
            SELECT yil, transition_date, transition_hour,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk WHERE gun_tipi = 'hafta içi'
            GROUP BY 1, 2, 3
        )
        SELECT yil, transition_hour AS saat, AVG(yolcu) AS ort
        FROM gunluk GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    fig, ax = plt.subplots()
    for renk, (yil, grup) in zip(YIL_RENKLERI, df.groupby("yil")):
        ax.plot(grup["saat"], grup["ort"] / 1000, color=renk,
                linewidth=2.2, label=str(yil))
    ax.set_title("Şehrin günlük ritmi yıldan yıla değişti mi? (hafta içi)")
    ax.set_xlabel("Saat")
    ax.set_ylabel("Ortalama yolcu (bin kişi/saat)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(title=None)
    kaydet(fig, "k2_saatlik_profil")


def k3_gece_endeksi(con, yillar):
    df = con.sql("""
        WITH raylik AS (
            SELECT y.yil,
                   COALESCE(y.town, m7.ilce) AS ilce,
                   y.transition_hour         AS saat,
                   y.number_of_passenger     AS yolcu
            FROM yolculuk y
            LEFT JOIN read_csv('veri/esleme/m7_istasyon_ilce.csv', header=true) m7
                   ON y.line_name = 'M7' AND y.station_poi_desc_cd = m7.istasyon
            WHERE y.road_type = 'RAYLI'
        )
        SELECT yil, ilce,
               ROUND(1000.0 * SUM(yolcu) FILTER (saat >= 23 OR saat < 5)
                            / SUM(yolcu), 1) AS gece_endeksi,
               SUM(yolcu) AS toplam
        FROM raylik
        WHERE ilce IS NOT NULL
        GROUP BY 1, 2
        HAVING SUM(yolcu) > 500_000
        ORDER BY 1, 3 DESC
    """).df()
    son_yil = max(yillar)
    top = (df[df["yil"] == son_yil].nlargest(10, "gece_endeksi")["ilce"].tolist())
    df = df[df["ilce"].isin(top)]
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(df, x="gece_endeksi", y="ilce", hue="yil", order=top,
                palette=YIL_RENKLERI[:len(yillar)], ax=ax)
    ax.set_title("Gece hayatı hangi ilçede nasıl değişti?")
    ax.set_xlabel("Gece yolcu payı (binde, 23:00–05:00) — raylı sistem")
    ax.set_ylabel("")
    ax.legend(title=None)
    kaydet(fig, "k3_gece_endeksi")


if __name__ == "__main__":
    yillar = sorted({int(p.stem.split("_")[1][:4])
                     for p in PROCESSED.glob("hourly_*.parquet")})
    if len(yillar) < 2:
        sys.exit("Kıyas için en az 2 yılın Parquet'i gerekli.")
    print(f"kıyaslanan yıllar: {yillar}")
    stil()
    con = baglan()  # yıl filtresi yok: tüm yıllar
    k1_aylik_hacim(con, yillar)
    k2_saatlik_profil(con, yillar)
    k3_gece_endeksi(con, yillar)
