-- SORU: Şehrin ritmi mevsimden mevsime nasıl değişiyor?
--       Hangi ay yıl ortalamasının üstünde/altında, gece hayatı hangi ayda canlı?
-- Yöntem: Ay bazında ortalama günlük yolcu; AVG() OVER () ile yıl ortalamasına
--         göre sapma; FILTER ile ay bazında gece payı.

WITH gunluk AS (
    SELECT
        transition_date,
        ay,
        SUM(number_of_passenger)                                    AS yolcu,
        SUM(number_of_passenger) FILTER (transition_hour >= 23
                                      OR transition_hour < 5)       AS gece_yolcu
    FROM yolculuk
    GROUP BY 1, 2
),
aylik AS (
    SELECT
        ay,
        AVG(yolcu)                              AS ort_gunluk_yolcu,
        SUM(gece_yolcu) * 1000.0 / SUM(yolcu)   AS gece_endeksi  -- binde
    FROM gunluk
    GROUP BY 1
)
SELECT
    ay,
    ROUND(ort_gunluk_yolcu)                                             AS ort_gunluk_yolcu,
    ROUND(100.0 * ort_gunluk_yolcu / AVG(ort_gunluk_yolcu) OVER () - 100, 1)
                                                                        AS yil_ort_sapma_pct,
    ROUND(gece_endeksi, 1)                                              AS gece_endeksi
FROM aylik
ORDER BY ay;
