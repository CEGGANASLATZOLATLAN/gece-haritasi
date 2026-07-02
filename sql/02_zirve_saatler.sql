-- SORU: Her raylı sistem istasyonunun zirve saati kaç?
--       Şehrin "sabah istasyonları" ve "akşam istasyonları" hangileri?
-- Yöntem: ROW_NUMBER() OVER (PARTITION BY istasyon ORDER BY yolcu DESC)
--         → her istasyonun 1 numaralı saati. Hafta içi trafiğine bakıyoruz.
-- Not: Otobüs istasyon bazında kaydedilmediği için sadece RAYLI (bkz. VERI_SOZLUGU.md).

WITH istasyon_saat AS (
    SELECT
        line_name             AS hat,
        station_poi_desc_cd   AS istasyon,
        transition_hour       AS saat,
        SUM(number_of_passenger) AS yolcu
    FROM yolculuk
    WHERE road_type = 'RAYLI'
      AND station_poi_desc_cd IS NOT NULL
      AND gun_tipi = 'hafta içi'
    GROUP BY 1, 2, 3
),
sirali AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY hat, istasyon
            ORDER BY yolcu DESC
        ) AS sira,
        SUM(yolcu) OVER (PARTITION BY hat, istasyon) AS istasyon_toplam
    FROM istasyon_saat
)
SELECT
    hat,
    istasyon,
    saat                                            AS zirve_saat,
    yolcu                                           AS zirve_saat_yolcu,
    istasyon_toplam,
    ROUND(100.0 * yolcu / istasyon_toplam, 1)       AS zirve_pay_pct
FROM sirali
WHERE sira = 1
ORDER BY istasyon_toplam DESC;
