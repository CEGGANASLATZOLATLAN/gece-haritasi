-- SORU: İstanbul'un hangi ilçesi gece yaşıyor?
-- Yöntem: Gece = 23:00–04:59 arası. Her ilçenin toplam raylı yolcusu içinde
--         gece payı. FILTER ile koşullu toplam.
-- Not: town kolonu sadece RAYLI'da istasyonun gerçek ilçesi (bkz. VERI_SOZLUGU.md);
--      otobüste garaj bölgesi olduğu için dahil edilmedi. M7'nin ilçesi kaynakta
--      NULL, veri/esleme/m7_istasyon_ilce.csv ile tamamlanıyor.

WITH raylik AS (
    SELECT
        COALESCE(y.town, m7.ilce) AS ilce,
        y.transition_hour         AS saat,
        y.number_of_passenger     AS yolcu
    FROM yolculuk y
    LEFT JOIN read_csv('veri/esleme/m7_istasyon_ilce.csv', header=true) m7
           ON y.line_name = 'M7' AND y.station_poi_desc_cd = m7.istasyon
    WHERE y.road_type = 'RAYLI'
)
SELECT
    ilce,
    SUM(yolcu)                                          AS toplam_yolcu,
    SUM(yolcu) FILTER (saat >= 23 OR saat < 5)          AS gece_yolcu,
    ROUND(1000.0 * SUM(yolcu) FILTER (saat >= 23 OR saat < 5)
                 / SUM(yolcu), 1)                       AS gece_endeksi  -- binde
FROM raylik
WHERE ilce IS NOT NULL
GROUP BY 1
HAVING SUM(yolcu) > 1_000_000   -- çok küçük ilçelerde oran yanıltıcı
ORDER BY gece_endeksi DESC;
