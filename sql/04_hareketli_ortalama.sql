-- SORU: 2023 boyunca günlük toplam yolculuk nasıl seyretti?
--       Trend (7 günlük hareketli ortalama) ve günün trendden sapması ne?
-- Yöntem: AVG() OVER (ORDER BY ... ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
--         Sapma yüzdesi bayram/özel gün anomalilerini yakalamak için temel.

WITH gunluk AS (
    SELECT
        transition_date,
        SUM(number_of_passenger) AS yolcu
    FROM yolculuk
    GROUP BY 1
)
SELECT
    transition_date,
    yolcu,
    ROUND(AVG(yolcu) OVER (
        ORDER BY transition_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ))                                                   AS hareketli_ort_7g,
    ROUND(100.0 * yolcu / AVG(yolcu) OVER (
        ORDER BY transition_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) - 100, 1)                                          AS trendden_sapma_pct
FROM gunluk
ORDER BY transition_date;
