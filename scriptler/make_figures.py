"""Bir yılın tüm analiz grafiklerini üretir (Faz 3-4).

Kullanım (proje kökünden):
    python scriptler/make_figures.py 2023

Çıktılar: ciktilar/grafikler/<yil>/*.png ve ciktilar/haritalar/ilce_saatlik_nabiz_<yil>.html
Önkoşul: o yılın ayları ingest edilmiş olmalı (veri/islenmis/hourly_<yil>MM.parquet).
Kısmi yıllar (ör. 2024 Ocak-Temmuz) da çalışır; grafikler mevcut aylarla çizilir.
"""

import argparse
import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOKU))

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from kaynak.db import PROCESSED, baglan, sql_dosyasi_calistir
from kaynak.viz import MAPS, RENKLER, kaydet, stil

SQL = PROJE_KOKU / "sql"

# Yıl bazında özel günler. Yıllık seyir grafiğinde işaretlenir; anomali
# grafiğinde |z|>=2 çıkan gün burada varsa etiketlenir, yoksa tarih yazılır.
# Yeni bir yıl işlerken o yılın olaylarını buraya ekleyin.
OZEL_GUNLER = {
    2022: {
        "2022-01-01": "Yılbaşı",
        "2022-01-24": "Kar fırtınası 1. gün",
        "2022-01-25": "Kar fırtınası 2. gün",
        "2022-05-01": "Ramazan B. arifesi",
        "2022-05-02": "Ramazan Bayramı",
        "2022-07-08": "Kurban B. arifesi",
        "2022-07-09": "Kurban Bayramı",
        "2022-09-05": "Okullar açıldı",
        "2022-10-29": "Cumhuriyet Bayramı",
    },
    2023: {
        "2023-01-01": "Yılbaşı",
        "2023-02-05": "Kar yağışı",
        "2023-02-06": "6 Şubat depremi",
        "2023-04-20": "Ramazan B. arifesi",
        "2023-04-21": "Ramazan B. 1. günü",
        "2023-04-23": "23 Nisan + bayramın 3. günü",
        "2023-05-14": "Seçim 1. tur",
        "2023-05-28": "Seçim 2. tur",
        "2023-06-27": "Kurban B. arifesi",
        "2023-06-28": "Kurban Bayramı",
        "2023-09-11": "Okullar açıldı",
        "2023-10-28": "100. yıl arifesi",
        "2023-10-29": "Cumhuriyet'in 100. yılı",
        "2023-11-18": "Lodos fırtınası",
    },
    2024: {
        "2024-01-01": "Yılbaşı",
        "2024-03-31": "Yerel seçim",
        "2024-04-10": "Ramazan Bayramı",
        "2024-06-16": "Kurban Bayramı",
    },
}

# Yıllık seyir grafiğinde kalabalık olmasın diye işaretlenecek alt küme
SEYIR_ETIKETLERI = {
    2023: ["2023-01-01", "2023-02-06", "2023-04-21", "2023-05-14",
           "2023-05-28", "2023-06-28", "2023-09-11", "2023-10-29"],
}

GUN_ADLARI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
TR_AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
            "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def tr_ay_ekseni(ax):
    """X eksenindeki ay adlarını Türkçeleştirir."""
    import matplotlib.ticker as mticker
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: TR_AYLAR[mdates.num2date(x).month - 1]))


def tr_tarih(t: pd.Timestamp) -> str:
    return f"{t.day} {TR_AYLAR[t.month - 1]}"


def fig_01_saatlik_nabiz(con, yil):
    df = sql_dosyasi_calistir(con, SQL / "01_saatlik_profil.sql").df()
    fig, ax = plt.subplots()
    for tip, grup in df.groupby("gun_tipi"):
        ax.plot(grup["saat"], grup["ortalama_yolcu"] / 1000,
                label=tip, color=RENKLER[tip], linewidth=2.5)
    ax.set_title(f"İstanbul kaçta uyanıyor, kaçta yatıyor? ({yil})")
    ax.set_xlabel("Saat")
    ax.set_ylabel("Ortalama yolcu (bin kişi/saat)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(title=None)
    kaydet(fig, "fig_01_saatlik_nabiz", yil)


def fig_02_isi_haritasi(con, yil):
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
    ax.set_title(f"Şehrin nabzı: hangi gün, hangi saat? ({yil})")
    ax.set_xlabel("Saat")
    ax.set_ylabel("")
    kaydet(fig, "fig_02_isi_haritasi", yil)


def fig_03_yillik_seyir(con, yil):
    df = sql_dosyasi_calistir(con, SQL / "04_hareketli_ortalama.sql").df()
    df["transition_date"] = pd.to_datetime(df["transition_date"])
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df["transition_date"], df["yolcu"] / 1e6,
            color=RENKLER["notr"], linewidth=0.8, alpha=0.7, label="Günlük yolcu")
    ax.plot(df["transition_date"], df["hareketli_ort_7g"] / 1e6,
            color=RENKLER["hafta içi"], linewidth=2.2, label="7 günlük hareketli ort.")
    etiketler = SEYIR_ETIKETLERI.get(yil, list(OZEL_GUNLER.get(yil, {})))
    for tarih in etiketler:
        eslesen = df.loc[df["transition_date"] == pd.Timestamp(tarih), "yolcu"]
        if eslesen.empty:   # kısmi yılda o gün yoksa atla
            continue
        ad = OZEL_GUNLER[yil][tarih]
        t = pd.Timestamp(tarih)
        ax.annotate(ad, (t, float(eslesen.iloc[0]) / 1e6),
                    textcoords="offset points", xytext=(0, -28),
                    ha="center", fontsize=8, color=RENKLER["vurgu"],
                    arrowprops=dict(arrowstyle="-", color=RENKLER["vurgu"], lw=0.8))
    ax.set_title(f"{yil}'te İstanbul ne zaman durdu, ne zaman coştu?")
    ax.set_xlabel("")
    ax.set_ylabel("Günlük toplam yolcu (milyon)")
    tr_ay_ekseni(ax)
    ax.legend(loc="lower right")
    kaydet(fig, "fig_03_yillik_seyir", yil)


def fig_04_anomali(con, yil):
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
    ozel = OZEL_GUNLER.get(yil, {})
    # Sözlükte adı olan her anomaliyi etiketle; kalanlardan en uç 6'ya tarih yaz
    en_uc = set(anomali.reindex(anomali["z"].abs()
                                .sort_values(ascending=False).index).head(6).index)
    for idx, r in anomali.iterrows():
        gun = str(r["transition_date"].date())
        if gun in ozel:
            etiket = ozel[gun]
        elif idx in en_uc:
            etiket = tr_tarih(r["transition_date"])
        else:
            continue
        yukari = r["z"] > 0
        ax.annotate(etiket, (r["transition_date"], r["z"]),
                    textcoords="offset points",
                    xytext=(6, 8 if yukari else -14), fontsize=8)
    ax.set_title(f"Hangi günler 'normal' değildi? ({yil})")
    ax.set_xlabel("")
    ax.set_ylabel("Z-skoru (aynı haftanın gününe göre)")
    tr_ay_ekseni(ax)
    ax.legend(loc="upper left")
    kaydet(fig, "fig_04_anomali", yil)


def fig_05_gece_ilceler(con, yil):
    df = sql_dosyasi_calistir(con, SQL / "05_gece_endeksi.sql").df().head(12)
    df = df.sort_values("gece_endeksi")
    fig, ax = plt.subplots(figsize=(10, 6))
    renkler = [RENKLER["vurgu"] if i == len(df) - 1 else RENKLER["hafta içi"]
               for i in range(len(df))]
    ax.barh(df["ilce"], df["gece_endeksi"], color=renkler)
    for _, r in df.iterrows():
        ax.text(r["gece_endeksi"] + 0.5, r["ilce"], f"‰{r['gece_endeksi']:.0f}",
                va="center", fontsize=9)
    ax.set_title(f"İstanbul'un gece başkenti neresi? ({yil})")
    ax.set_xlabel("Gece yolcu payı (binde, 23:00–05:00) — raylı sistem istasyonları")
    kaydet(fig, "fig_05_gece_ilceler", yil)


def fig_06_istasyon_kumeleri(con, yil):
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
    ax.set_title(f"İstasyonların günlük ritmi kaç tipe ayrılıyor? ({yil})")
    ax.set_xlabel("Saat")
    ax.set_ylabel("Günlük yolcunun saatteki payı (%)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    kaydet(fig, "fig_06_istasyon_kumeleri", yil)


def harita_ilce_nabiz(con, yil):
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
        title=f"İlçe ilçe şehrin nabzı, {yil} — saat kaydıracını oynat (raylı sistem)",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"},
                      annotations=[dict(text=f"Kaynak: İBB Açık Veri ({yil})",
                                        x=1, y=-0.12, xref="paper", yref="paper",
                                        showarrow=False, font=dict(size=10, color="gray"))])
    yol = MAPS / f"ilce_saatlik_nabiz_{yil}.html"
    fig.write_html(yol, include_plotlyjs="cdn")
    print(f"kaydedildi: {yol.relative_to(PROJE_KOKU)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("yil", type=int, help="Analiz edilecek yıl, ör. 2023")
    yil = p.parse_args().yil

    if not list(PROCESSED.glob(f"hourly_{yil}*.parquet")):
        sys.exit(f"veri/islenmis/ altında {yil} Parquet'i yok. "
                 f"Önce: python kaynak/ingest.py")
    stil()
    con = baglan(yil)
    fig_01_saatlik_nabiz(con, yil)
    fig_02_isi_haritasi(con, yil)
    fig_03_yillik_seyir(con, yil)
    fig_04_anomali(con, yil)
    fig_05_gece_ilceler(con, yil)
    fig_06_istasyon_kumeleri(con, yil)
    harita_ilce_nabiz(con, yil)
