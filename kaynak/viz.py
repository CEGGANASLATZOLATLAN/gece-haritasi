"""Grafik yardımcıları: ortak stil, kaynak notu, kaydetme.

Grafik standardı (CLAUDE.md):
- Başlık bir SORUYA cevap verir
- Eksen etiketleri Türkçe
- Kaynak notu sağ altta
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

PROJE_KOKU = Path(__file__).resolve().parent.parent
FIGURES = PROJE_KOKU / "ciktilar" / "grafikler"
MAPS = PROJE_KOKU / "ciktilar" / "haritalar"
KAYNAK_NOTU = "Kaynak: İBB Açık Veri (Saatlik Toplu Ulaşım Veri Seti, 2023)"

RENKLER = {
    "hafta içi": "#1f6f8b",
    "hafta sonu": "#e4572e",
    "vurgu": "#c1121f",
    "notr": "#8d99ae",
}


def stil() -> None:
    sns.set_theme(style="whitegrid", font_scale=1.05)
    plt.rcParams["figure.figsize"] = (11, 6)
    plt.rcParams["axes.titlesize"] = 15
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["figure.constrained_layout.use"] = False


def kaydet(fig, ad: str) -> None:
    """Kaynak notunu basıp ciktilar/grafikler/<ad>.png olarak kaydeder."""
    fig.text(0.99, -0.01, KAYNAK_NOTU, ha="right", va="top",
             fontsize=8, color="gray")
    yol = FIGURES / f"{ad}.png"
    fig.savefig(yol, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"kaydedildi: {yol.relative_to(PROJE_KOKU)}")
