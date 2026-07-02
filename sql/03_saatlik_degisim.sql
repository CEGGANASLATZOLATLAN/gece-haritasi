-- SORU: İstanbul kaçta "patlıyor"? Saatten saate en sert sıçrama hangi saatte?
-- Yöntem: LAG() ile bir önceki saate göre mutlak ve yüzdesel değişim.
--         Hafta içi ortalama günü üzerinden.

WITH saatlik AS (
    SELECT
        transition_hour AS saat,
        SUM(number_of_passenger) * 1.0
            / COUNT(DISTINCT transition_date) AS ort_yolcu
    FROM yolculuk
    WHERE gun_tipi = 'hafta içi'
    GROUP BY 1
)
SELECT
    saat,
    ROUND(ort_yolcu)                                        AS ort_yolcu,
    ROUND(ort_yolcu - LAG(ort_yolcu) OVER (ORDER BY saat))  AS onceki_saate_fark,
    ROUND(100.0 * (ort_yolcu - LAG(ort_yolcu) OVER (ORDER BY saat))
               / LAG(ort_yolcu) OVER (ORDER BY saat), 1)    AS degisim_pct
FROM saatlik
ORDER BY saat;
