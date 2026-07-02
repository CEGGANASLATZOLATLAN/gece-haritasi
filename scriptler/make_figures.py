"""Tüm analiz grafiklerini üretir (Faz 3-4).

Kullanım (proje kökünden):
    python scriptler/make_figures.py

Çıktılar: ciktilar/grafikler/*.png ve ciktilar/haritalar/*.html
Her grafik sql/ altındaki bir sorguya ya da buradaki bir analiz sorgusuna dayanır.
"""

import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOKU))

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from kaynak.db import baglan, sql_dosyasi_calistir
from kaynak.viz import MAPS, RENKLER, kaydet, stil

SQL = PROJE_KOKU / "sql"

# 2023 özel günleri (yıllık seyir grafiğinde işaretlenir)
OZEL_GUNLER = {
    "2023-01-01": "Yılbaşı",
    "2023-02-06": "6 Şubat depremi",
    "2023-04-21": "Ramazan Bayramı",
    "2023-05-14": "Seçim 1. tur",
    "2023-05-28": "Seçim 2. tur",
    "2023-06-28": "Kurban Bayramı",
    "2023-09-11": "Okullar açıldı",
    "2023-10-29": "Cumhuriyet'in 100. yılı",
}

# Anomali grafiği etiketleri (web'den doğrulanmış olaylar)
ANOMALI_ETIKETLERI = {
    "2023-02-05": "Kar yağışı",
    "2023-02-06": "Deprem haftası",
    "2023-04-21": "Ramazan B. 1. günü",
    "2023-04-23": "23 Nisan + bayramın 3. günü",
    "2023-05-14": "Seçim 1. tur",
    "2023-06-27": "Kurban B. arifesi",
    "2023-10-28": "100. yıl arifesi",
    "2023-10-29": "Cumhuriyet'in 100. yılı",
    "2023-11-18": "Lodos fırtınası",
}

GUN_ADLARI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
TR_AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
            "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def tr_ay_ekseni(ax):
    """X eksenindeki ay adlarını Türkçeleştirir."""
    import matplotlib.ticker as mticker
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: TR_AYLAR[mdates.num2date(x).month - 1]))


def fig_01_saatlik_nabiz(con):
    df = sql_dosyasi_calistir(con, SQL / "01_saatlik_profil.sql").df()
    fig, ax = plt.subplots()
    for tip, grup in df.groupby("gun_tipi"):
        ax.plot(grup["saat"], grup["ortalama_yolcu"] / 1000,
                label=tip, color=RENKLER[tip], linewidth=2.5)
    ax.set_title("İstanbul kaçta uyanıyor, kaçta yatıyor?")
    ax.set_xlabel("Saat")
    ax.set_ylabel("Ortalama yolcu (bin kişi/saat)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(title=None)
    kaydet(fig, "fig_01_saatlik_nabiz")


def fig_02_isi_haritasi(con):
    import seaborn as sns
    df = con.sql("""
        WITH gunluk AS (
            SELECT transition_date, haftanin_gunu, transition_hour,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk GROUP BY 1, 2, 3
        )
        SELECT haftanin_gunu, transition_hour AS saat, AVG(yolcu) AS ort
        FROM gunluk GROUP BY 1, 2
    """).df()
    pivot = df.pivot(index="haftanin_gunu", columns="saat", values="ort") / 1000
    pivot.index = [GUN_ADLARI[i - 1] for i in pivot.index]
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(pivot, cmap="rocket_r", ax=ax,
                cbar_kws={"label": "Ortalama yolcu (bin/saat)"})
    ax.set_title("Şehrin nabzı: hangi gün, hangi saat?")
    ax.set_xlabel("Saat")
    ax.set_ylabel("")
    kaydet(fig, "fig_02_isi_haritasi")


def fig_03_yillik_seyir(con):
    df = sql_dosyasi_calistir(con, SQL / "04_hareketli_ortalama.sql").df()
    df["transition_date"] = pd.to_datetime(df["transition_date"])
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df["transition_date"], df["yolcu"] / 1e6,
            color=RENKLER["notr"], linewidth=0.8, alpha=0.7, label="Günlük yolcu")
    ax.plot(df["transition_date"], df["hareketli_ort_7g"] / 1e6,
            color=RENKLER["hafta içi"], linewidth=2.2, label="7 günlük hareketli ort.")
    for tarih, ad in OZEL_GUNLER.items():
        t = pd.Timestamp(tarih)
        y = float(df.loc[df["transition_date"] == t, "yolcu"].iloc[0]) / 1e6
        ax.annotate(ad, (t, y), textcoords="offset points", xytext=(0, -28),
                    ha="center", fontsize=8, color=RENKLER["vurgu"],
                    arrowprops=dict(arrowstyle="-", color=RENKLER["vurgu"], lw=0.8))
    ax.set_title("2023'te İstanbul ne zaman durdu, ne zaman coştu?")
    ax.set_xlabel("")
    ax.set_ylabel("Günlük toplam yolcu (milyon)")
    tr_ay_ekseni(ax)
    ax.legend(loc="lower right")
    kaydet(fig, "fig_03_yillik_seyir")


def fig_04_anomali(con):
    # Z-score: her gün, kendi haftanın-günü popülasyonuyla kıyaslanır
    df = con.sql("""
        WITH gunluk AS (
            SELECT transition_date, haftanin_gunu,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk GROUP BY 1, 2
        )
        SELECT transition_date, haftanin_gunu, yolcu,
               (yolcu - AVG(yolcu) OVER (PARTITION BY haftanin_gunu))
                   / STDDEV(yolcu) OVER (PARTITION BY haftanin_gunu) AS z
        FROM gunluk ORDER BY transition_date
    """).df()
    df["transition_date"] = pd.to_datetime(df["transition_date"])
    fig, ax = plt.subplots(figsize=(13, 6))
    normal = df[df["z"].abs() < 2]
    anomali = df[df["z"].abs() >= 2]
    ax.scatter(normal["transition_date"], normal["z"], s=12,
               color=RENKLER["notr"], alpha=0.6, label="Normal gün")
    ax.scatter(anomali["transition_date"], anomali["z"], s=28,
               color=RENKLER["vurgu"], label="Anomali (|z| ≥ 2)")
    ax.axhline(2, ls="--", lw=0.8, color="gray")
    ax.axhline(-2, ls="--", lw=0.8, color="gray")
    for _, r in anomali.iterrows():
        gun = str(r["transition_date"].date())
        if gun not in ANOMALI_ETIKETLERI:
            continue
        yukari = r["z"] > 0
        ax.annotate(ANOMALI_ETIKETLERI[gun], (r["transition_date"], r["z"]),
                    textcoords="offset points",
                    xytext=(6, 8 if yukari else -14), fontsize=8)
    ax.set_title("Hangi günler 'normal' değildi?")
    ax.set_xlabel("")
    ax.set_ylabel("Z-skoru (aynı haftanın gününe göre)")
    tr_ay_ekseni(ax)
    ax.legend(loc="upper left")
    kaydet(fig, "fig_04_anomali")


def fig_05_gece_ilceler(con):
    df = sql_dosyasi_calistir(con, SQL / "05_gece_endeksi.sql").df().head(12)
    df = df.sort_values("gece_endeksi")
    fig, ax = plt.subplots(figsize=(10, 6))
    renkler = [RENKLER["vurgu"] if i == len(df) - 1 else RENKLER["hafta içi"]
               for i in range(len(df))]
    ax.barh(df["ilce"], df["gece_endeksi"], color=renkler)
    for _, r in df.iterrows():
        ax.text(r["gece_endeksi"] + 0.5, r["ilce"], f"‰{r['gece_endeksi']:.0f}",
                va="center", fontsize=9)
    ax.set_title("İstanbul'un gece başkenti neresi?")
    ax.set_xlabel("Gece yolcu payı (binde, 23:00–05:00) — raylı sistem istasyonları")
    kaydet(fig, "fig_05_gece_ilceler")


def fig_06_istasyon_kumeleri(con):
    from sklearn.cluster import KMeans

    # Her istasyonun hafta içi saatlik profili, günlük toplamına oranlanmış
    df = con.sql("""
        WITH saatlik AS (
            SELECT line_name || ' / ' || station_poi_desc_cd AS istasyon,
                   transition_hour AS saat,
                   SUM(number_of_passenger) AS yolcu
            FROM yolculuk
            WHERE road_type = 'RAYLI' AND station_poi_desc_cd IS NOT NULL
              AND gun_tipi = 'hafta içi'
            GROUP BY 1, 2
        )
        SELECT istasyon, saat,
               yolcu * 1.0 / SUM(yolcu) OVER (PARTITION BY istasyon) AS pay
        FROM saatlik
        QUALIFY SUM(yolcu) OVER (PARTITION BY istasyon) > 100000
    """).df()
    mat = df.pivot(index="istasyon", columns="saat", values="pay").fillna(0)
    km = KMeans(n_clusters=4, n_init=10, random_state=42).fit(mat)
    mat["kume"] = km.labels_

    # Kümeleri sabah/akşam oranına göre SIRALAYIP adlandır — böylece
    # iki küme aynı adı alamaz (oran eşiğiyle adlandırma çakışıyordu)
    profiller = {k: g.drop(columns="kume").mean() for k, g in mat.groupby("kume")}
    boyutlar = {k: len(g) for k, g in mat.groupby("kume")}
    oranlar = {k: p.loc[16:19].sum() / p.loc[6:9].sum() for k, p in profiller.items()}
    sirali = sorted(oranlar, key=oranlar.get)  # küçük→büyük: sabahçıdan akşamcıya
    ADLAR = ["Sabah zirveli (yatak odası)", "Çift zirveli (dengeli)",
             "Akşam ağırlıklı (karma-merkez)", "Sert akşam zirveli (iş/merkez)"]
    fig, ax = plt.subplots()
    for ad, kume in zip(ADLAR, sirali):
        profil = profiller[kume]
        ax.plot(profil.index, profil * 100, linewidth=2.2,
                label=f"{ad} — {boyutlar[kume]} istasyon")
    ax.set_title("İstasyonların günlük ritmi kaç tipe ayrılıyor?")
    ax.set_xlabel("Saat")
    ax.set_ylabel("Günlük yolcunun saatteki payı (%)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    kaydet(fig, "fig_06_istasyon_kumeleri")


def harita_ilce_nabiz(con):
    """İnteraktif HTML: ilçelerin (raylı) saatlik nabzı, saat kaydıraçlı."""
    import plotly.express as px

    df = con.sql("""
        WITH gunluk AS (
            SELECT y.transition_date,
                   COALESCE(y.town, m7.ilce) AS ilce,
                   y.transition_hour AS saat,
                   SUM(y.number_of_passenger) AS yolcu
            FROM yolculuk y
            LEFT JOIN read_csv('veri/esleme/m7_istasyon_ilce.csv', header=true) m7
                   ON y.line_name = 'M7' AND y.station_poi_desc_cd = m7.istasyon
            WHERE y.road_type = 'RAYLI' AND y.gun_tipi = 'hafta içi'
            GROUP BY 1, 2, 3
        )
        SELECT ilce, saat, AVG(yolcu) AS ort_yolcu
        FROM gunluk
        WHERE ilce IN (
            SELECT COALESCE(town, 'X') FROM yolculuk WHERE road_type='RAYLI'
            GROUP BY 1 ORDER BY SUM(number_of_passenger) DESC LIMIT 15
        )
        GROUP BY 1, 2 ORDER BY 2, 3 DESC
    """).df()
    fig = px.bar(
        df, x="ort_yolcu", y="ilce", animation_frame="saat", orientation="h",
        range_x=[0, df["ort_yolcu"].max() * 1.05],
        labels={"ort_yolcu": "Ortalama yolcu (hafta içi)", "ilce": "", "saat": "Saat"},
        title="İlçe ilçe şehrin nabzı — saat kaydıracını oynat (raylı sistem)",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"},
                      annotations=[dict(text="Kaynak: İBB Açık Veri",
                                        x=1, y=-0.12, xref="paper", yref="paper",
                                        showarrow=False, font=dict(size=10, color="gray"))])
    yol = MAPS / "ilce_saatlik_nabiz.html"
    fig.write_html(yol, include_plotlyjs="cdn")
    print(f"kaydedildi: {yol.relative_to(PROJE_KOKU)}")


if __name__ == "__main__":
    stil()
    con = baglan()
    fig_01_saatlik_nabiz(con)
    fig_02_isi_haritasi(con)
    fig_03_yillik_seyir(con)
    fig_04_anomali(con)
    fig_05_gece_ilceler(con)
    fig_06_istasyon_kumeleri(con)
    harita_ilce_nabiz(con)
