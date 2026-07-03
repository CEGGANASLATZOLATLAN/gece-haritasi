"""Özel analizler: kart tipleri, Ramazan imzası, günlerin kişiliği.

Kullanım (proje kökünden):
    python scriptler/ozel_analizler.py

Çıktılar: ciktilar/grafikler/ozel/
Veri: 2023 tam yıl temel alınır; Ramazan analizi 2023 + 2024'ü birlikte kullanır.
"""

import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOKU))

import matplotlib.pyplot as plt

from kaynak.db import baglan, sql_dosyasi_calistir
from kaynak.viz import FIGURES, RENKLER, stil

CIKTI = FIGURES / "ozel"
KAYNAK = "Kaynak: İBB Açık Veri (Saatlik Toplu Ulaşım Veri Seti)"

KART_ADLARI = {
    "TAM": "Tam",
    "INDIRIMLI1": "İndirimli-1 (öğrenci ağırlıklı)",
    "INDIRIMLI2": "İndirimli-2",
    "UCRETSIZ": "Ücretsiz (65+, engelli)",
}
KART_RENKLERI = {
    "TAM": "#1f6f8b", "INDIRIMLI1": "#e4572e",
    "INDIRIMLI2": "#8d99ae", "UCRETSIZ": "#9d4edd",
}

# Diyanet takvimine göre Ramazan dönemleri (bayram hariç)
RAMAZAN = {2023: ("2023-03-23", "2023-04-20"),
           2024: ("2024-03-11", "2024-04-09")}


def kaydet(fig, ad):
    fig.text(0.99, -0.01, KAYNAK, ha="right", va="top", fontsize=8, color="gray")
    CIKTI.mkdir(parents=True, exist_ok=True)
    yol = CIKTI / f"{ad}.png"
    fig.savefig(yol, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"kaydedildi: {yol.relative_to(PROJE_KOKU)}")


def fig_07_kart_tipi(con):
    df = sql_dosyasi_calistir(con, PROJE_KOKU / "sql/07_kart_tipi.sql").df()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    for kart, grup in df.groupby("kart"):
        ax1.plot(grup["saat"], grup["gun_ici_pay_pct"],
                 label=KART_ADLARI[kart], color=KART_RENKLERI[kart], linewidth=2.2)
    ax1.set_title("Kim hangi saatte yolda? (hafta içi, 2023)")
    ax1.set_xlabel("Saat")
    ax1.set_ylabel("Grubun günlük yolcusundaki payı (%)")
    ax1.set_xticks(range(0, 24, 2))
    ax1.legend(fontsize=9)

    # Öğrenci profili: okul dönemi (Mart) vs yaz tatili (Temmuz)
    ogr = con.sql("""
        WITH g AS (
            SELECT CASE WHEN ay = 3 THEN 'Okul dönemi (Mart)'
                        ELSE 'Yaz tatili (Temmuz)' END AS donem,
                   transition_hour AS saat,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk
            WHERE gun_tipi = 'hafta içi' AND product_kind = 'INDIRIMLI1'
              AND ay IN (3, 7)
            GROUP BY 1, 2
        )
        SELECT donem, saat,
               100.0 * yolcu / SUM(yolcu) OVER (PARTITION BY donem) AS pay
        FROM g ORDER BY donem, saat
    """).df()
    for (donem, grup), renk in zip(ogr.groupby("donem"),
                                   [RENKLER["hafta içi"], RENKLER["hafta sonu"]]):
        ax2.plot(grup["saat"], grup["pay"], label=donem, color=renk, linewidth=2.2)
    ax2.set_title("Öğrenci kartı yazın başka bir şehirde: okul vs tatil")
    ax2.set_xlabel("Saat")
    ax2.set_ylabel("Günlük yolcudaki pay (%)")
    ax2.set_xticks(range(0, 24, 2))
    ax2.legend(fontsize=9)
    kaydet(fig, "fig_07_kart_tipi")


def fig_08_ramazan(con_tum):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Panel A: 2024 hafta içi profili — Ramazan vs aynı mevsimin geri kalanı
    df = con_tum.sql(f"""
        WITH g AS (
            SELECT CASE WHEN transition_date BETWEEN '{RAMAZAN[2024][0]}' AND '{RAMAZAN[2024][1]}'
                        THEN 'Ramazan' ELSE 'Normal dönem' END AS donem,
                   transition_date, transition_hour AS saat,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk
            WHERE yil = 2024 AND gun_tipi = 'hafta içi'
              AND transition_date BETWEEN '2024-02-01' AND '2024-05-31'
              AND transition_date NOT BETWEEN '2024-04-10' AND '2024-04-14'  -- bayram haftası hariç
            GROUP BY 1, 2, 3
        )
        SELECT donem, saat, AVG(yolcu) AS ort FROM g GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    for (donem, grup), renk in zip(df.groupby("donem"),
                                   [RENKLER["notr"], RENKLER["vurgu"]]):
        ax1.plot(grup["saat"], grup["ort"] / 1000, label=donem,
                 color=renk, linewidth=2.2)
    ax1.set_title("Ramazan şehrin ritmini nasıl büküyor? (2024, hafta içi)")
    ax1.set_xlabel("Saat")
    ax1.set_ylabel("Ortalama yolcu (bin/saat)")
    ax1.set_xticks(range(0, 24, 2))
    ax1.legend()

    # Panel B: gece saatlerinde (20:00-05:00) Ramazan/normal oranı, iki yıl
    oran = con_tum.sql(f"""
        WITH g AS (
            SELECT yil,
                   CASE WHEN (yil = 2023 AND transition_date BETWEEN '{RAMAZAN[2023][0]}' AND '{RAMAZAN[2023][1]}')
                          OR (yil = 2024 AND transition_date BETWEEN '{RAMAZAN[2024][0]}' AND '{RAMAZAN[2024][1]}')
                        THEN 'ramazan' ELSE 'normal' END AS donem,
                   transition_date, transition_hour AS saat,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk
            WHERE gun_tipi = 'hafta içi' AND yil IN (2023, 2024)
              AND ((yil = 2023 AND transition_date BETWEEN '2023-02-01' AND '2023-05-31'
                    AND transition_date NOT BETWEEN '2023-04-21' AND '2023-04-25')
                OR (yil = 2024 AND transition_date BETWEEN '2024-02-01' AND '2024-05-31'
                    AND transition_date NOT BETWEEN '2024-04-10' AND '2024-04-14'))
            GROUP BY 1, 2, 3, 4
        ),
        ort AS (
            SELECT yil, donem, saat, AVG(yolcu) AS ort FROM g GROUP BY 1, 2, 3
        )
        SELECT r.yil, r.saat, 100.0 * (r.ort / n.ort - 1) AS fark_pct
        FROM ort r JOIN ort n USING (yil, saat)
        WHERE r.donem = 'ramazan' AND n.donem = 'normal'
          AND (r.saat >= 20 OR r.saat <= 5)
        ORDER BY r.yil, (r.saat + 4) % 24
    """).df()
    saat_sira = [20, 21, 22, 23, 0, 1, 2, 3, 4, 5]
    for (yil, grup), renk in zip(oran.groupby("yil"),
                                 [RENKLER["hafta içi"], RENKLER["hafta sonu"]]):
        grup = grup.set_index("saat").loc[saat_sira].reset_index()
        ax2.plot(range(len(saat_sira)), grup["fark_pct"], marker="o",
                 label=f"Ramazan {yil}", color=renk, linewidth=2.2)
    ax2.axhline(0, color="gray", lw=0.8)
    ax2.set_xticks(range(len(saat_sira)))
    ax2.set_xticklabels([f"{s:02d}" for s in saat_sira])
    ax2.set_title("Gece Ramazan'da kaç kat canlanıyor?")
    ax2.set_xlabel("Saat (akşamdan sahura)")
    ax2.set_ylabel("Normal döneme göre fark (%)")
    ax2.legend()
    kaydet(fig, "fig_08_ramazan")


def fig_09_gunlerin_kisiligi(con):
    df = con.sql("""
        WITH g AS (
            SELECT haftanin_gunu, transition_date, transition_hour AS saat,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk GROUP BY 1, 2, 3
        )
        SELECT haftanin_gunu, saat, AVG(yolcu) AS ort
        FROM g GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    GUNLER = {1: "Pazartesi", 2: "Salı", 3: "Çarşamba", 4: "Perşembe",
              5: "Cuma", 6: "Cumartesi", 7: "Pazar"}
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for gun, grup in df.groupby("haftanin_gunu"):
        if gun in (2, 3, 4):   # orta hafta: gri arka plan
            stil_args = dict(color="#c8cfd8", linewidth=1.2, zorder=1)
        elif gun == 1:
            stil_args = dict(color=RENKLER["hafta içi"], linewidth=2.4, zorder=3)
        elif gun == 5:
            stil_args = dict(color="#2a9d8f", linewidth=2.4, zorder=3)
        elif gun == 6:
            stil_args = dict(color=RENKLER["hafta sonu"], linewidth=2.4, zorder=3)
        else:
            stil_args = dict(color=RENKLER["vurgu"], linewidth=2.4, zorder=3)
        ax.plot(grup["saat"], grup["ort"] / 1000, label=GUNLER[gun], **stil_args)
    ax.set_title("Haftanın her gününün ayrı bir kişiliği var mı? (2023)")
    ax.set_xlabel("Saat")
    ax.set_ylabel("Ortalama yolcu (bin/saat)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(fontsize=9, ncol=2)
    kaydet(fig, "fig_09_gunlerin_kisiligi")


if __name__ == "__main__":
    stil()
    con_2023 = baglan(2023)
    con_tum = baglan()
    fig_07_kart_tipi(con_2023)
    fig_08_ramazan(con_tum)
    fig_09_gunlerin_kisiligi(con_2023)
