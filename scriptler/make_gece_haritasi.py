"""Projeye adını veren harita: ilçe bazlı gece endeksi choropleth'i.

Kullanım (proje kökünden):
    python scriptler/make_gece_haritasi.py 2023

Çıktı: ciktilar/haritalar/gece_haritasi_<yil>.html (folium, tarayıcıda açılır)

Notlar:
- Gece endeksi = raylı sistem yolcusunda 23:00–05:00 payı (binde).
  town otobüste garaj bölgesi olduğu için sadece RAYLI kullanılır
  (bkz. veri/VERI_SOZLUGU.md); M7 lookup ile tamamlanır.
- İlçe sınırları: veri/esleme/istanbul_ilceler.geojson
  (kaynak: github.com/ozanyerli/istanbul-districts-geojson)
- Raylı sistemi olmayan ilçeler gri görünür; Marmaray'ın Kocaeli durakları
  (Gebze, Darıca...) İstanbul haritasında olmadığı için dışarıda kalır.
"""

import argparse
import json
import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOKU))

import folium

from kaynak.db import baglan
from kaynak.viz import MAPS

GEOJSON = PROJE_KOKU / "veri" / "esleme" / "istanbul_ilceler.geojson"


def normalize(ad: str) -> str:
    """'Kadıköy' → 'KADIKOY' (verideki town formatı)."""
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return ad.translate(tablo).upper()


def gece_endeksi(con) -> dict[str, float]:
    df = con.sql("""
        WITH raylik AS (
            SELECT COALESCE(y.town, m7.ilce) AS ilce,
                   y.transition_hour         AS saat,
                   y.number_of_passenger     AS yolcu
            FROM yolculuk y
            LEFT JOIN read_csv('veri/esleme/m7_istasyon_ilce.csv', header=true) m7
                   ON y.line_name = 'M7' AND y.station_poi_desc_cd = m7.istasyon
            WHERE y.road_type = 'RAYLI'
        )
        SELECT ilce,
               ROUND(1000.0 * SUM(yolcu) FILTER (saat >= 23 OR saat < 5)
                            / SUM(yolcu), 1) AS endeks
        FROM raylik WHERE ilce IS NOT NULL
        GROUP BY 1 HAVING SUM(yolcu) > 500_000
    """).df()
    return dict(zip(df["ilce"], df["endeks"]))


def main(yil: int) -> None:
    con = baglan(yil)
    endeks = gece_endeksi(con)

    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    for f in gj["features"]:
        ad = f["properties"]["name"]
        deger = endeks.get(normalize(ad))
        f["properties"]["gece_endeksi"] = (
            f"‰{deger:.1f}" if deger is not None else "raylı sistem yok")
        f["properties"]["_deger"] = deger

    m = folium.Map(location=[41.05, 28.95], zoom_start=10, tiles="cartodbpositron")

    # açık sarı → koyu mor (gece teması); gri = raylı sistem yok
    import branca.colormap as cm
    skala = cm.LinearColormap(
        ["#fff3b0", "#f4a261", "#e76f51", "#9d4edd", "#3c096c"],
        vmin=min(endeks.values()), vmax=max(endeks.values()),
        caption=f"Gece yolcu payı (binde, 23:00–05:00), {yil}")
    skala.add_to(m)

    def renk(v):
        return "#d9d9d9" if v is None else skala(v)

    folium.GeoJson(
        gj,
        style_function=lambda f: {
            "fillColor": renk(f["properties"]["_deger"]),
            "fillOpacity": 0.75, "color": "white", "weight": 1,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "gece_endeksi"],
            aliases=["İlçe", "Gece endeksi"]),
    ).add_to(m)

    baslik = (f'<h4 style="position:fixed;top:10px;left:50px;z-index:9999;'
              f'background:white;padding:6px 12px;border-radius:4px;'
              f'box-shadow:0 1px 4px rgba(0,0,0,.3)">'
              f'Gece Haritası — İstanbul geceleri nerede yaşıyor? ({yil})</h4>'
              f'<div style="position:fixed;bottom:10px;right:10px;z-index:9999;'
              f'background:white;padding:2px 8px;font-size:11px;color:gray">'
              f'Kaynak: İBB Açık Veri</div>')
    m.get_root().html.add_child(folium.Element(baslik))

    MAPS.mkdir(parents=True, exist_ok=True)
    yol = MAPS / f"gece_haritasi_{yil}.html"
    m.save(str(yol))
    print(f"kaydedildi: {yol.relative_to(PROJE_KOKU)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("yil", type=int)
    main(p.parse_args().yil)
