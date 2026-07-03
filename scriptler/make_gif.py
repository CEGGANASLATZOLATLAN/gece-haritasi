"""Animasyonlu ısı haritası: 24 saatte ilçe ilçe şehrin nabzı (GIF).

Kullanım (proje kökünden):
    python scriptler/make_gif.py 2023

Çıktı: ciktilar/grafikler/nabiz_24saat_<yil>.gif (README'ye gömülebilir)

Her ilçe kendi günlük zirvesine göre normalize edilir (0-1): harita "hangi
ilçe ne zaman canlı" sorusunu gösterir, hacim değil. Raylı sistem verisi
(town yalnızca raylı sistemde güvenilir; M7 lookup ile tamamlanır).
"""

import argparse
import json
import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOKU))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

from kaynak.db import baglan
from kaynak.viz import FIGURES

GEOJSON = PROJE_KOKU / "veri" / "esleme" / "istanbul_ilceler.geojson"


def normalize(ad: str) -> str:
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return ad.translate(tablo).upper()


def saatlik_nabiz(con) -> dict[str, np.ndarray]:
    """İlçe → 24 elemanlı dizi (kendi zirvesine göre 0-1)."""
    df = con.sql("""
        WITH gunluk AS (
            SELECT COALESCE(y.town, m7.ilce) AS ilce,
                   y.transition_date, y.transition_hour AS saat,
                   SUM(y.number_of_passenger) AS yolcu
            FROM yolculuk y
            LEFT JOIN read_csv('veri/esleme/m7_istasyon_ilce.csv', header=true) m7
                   ON y.line_name = 'M7' AND y.station_poi_desc_cd = m7.istasyon
            WHERE y.road_type = 'RAYLI' AND y.gun_tipi = 'hafta içi'
            GROUP BY 1, 2, 3
        )
        SELECT ilce, saat, AVG(yolcu) AS ort
        FROM gunluk WHERE ilce IS NOT NULL
        GROUP BY 1, 2
        QUALIFY SUM(SUM(yolcu)) OVER (PARTITION BY ilce) > 100000
        ORDER BY 1, 2
    """).df()
    nabiz = {}
    for ilce, grup in df.groupby("ilce"):
        dizi = np.zeros(24)
        dizi[grup["saat"].to_numpy()] = grup["ort"].to_numpy()
        if dizi.max() > 0:
            nabiz[ilce] = dizi / dizi.max()
    return nabiz


def poligonlar(feature) -> list[np.ndarray]:
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        halkalar = [geom["coordinates"]]
    else:  # MultiPolygon
        halkalar = geom["coordinates"]
    return [np.array(h[0]) for h in halkalar]  # sadece dış halka


def main(yil: int) -> None:
    con = baglan(yil)
    nabiz = saatlik_nabiz(con)
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))

    canli_patches, canli_ilceler, gri_patches = [], [], []
    for f in gj["features"]:
        ad = normalize(f["properties"]["name"])
        for koord in poligonlar(f):
            if ad in nabiz:
                canli_patches.append(Polygon(koord))
                canli_ilceler.append(ad)
            else:
                gri_patches.append(Polygon(koord))

    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    ax.set_aspect(1 / np.cos(np.radians(41)))
    ax.axis("off")
    ax.add_collection(PatchCollection(
        gri_patches, facecolor="#e8e8e8", edgecolor="white", linewidth=0.6))
    canli = PatchCollection(canli_patches, cmap="rocket_r",
                            edgecolor="white", linewidth=0.6)
    canli.set_clim(0, 1)
    ax.add_collection(canli)
    ax.autoscale_view()

    baslik = ax.set_title("", fontsize=15, fontweight="bold")
    fig.text(0.5, 0.04,
             "Her ilçe kendi günlük zirvesine göre (raylı sistem, hafta içi) — "
             "gri: raylı sistem yok", ha="center", fontsize=8, color="gray")
    fig.text(0.99, 0.01, f"Kaynak: İBB Açık Veri ({yil})",
             ha="right", fontsize=7, color="gray")

    def kare(saat):
        canli.set_array(np.array([nabiz[i][saat] for i in canli_ilceler]))
        baslik.set_text(f"İstanbul'un nabzı — saat {saat:02d}:00")
        return canli, baslik

    anim = FuncAnimation(fig, kare, frames=24)
    FIGURES.mkdir(parents=True, exist_ok=True)
    yol = FIGURES / f"nabiz_24saat_{yil}.gif"
    anim.save(yol, writer=PillowWriter(fps=2), dpi=110)
    plt.close(fig)
    print(f"kaydedildi: {yol.relative_to(PROJE_KOKU)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("yil", type=int)
    main(p.parse_args().yil)
