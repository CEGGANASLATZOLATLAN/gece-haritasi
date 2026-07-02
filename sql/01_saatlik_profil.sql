-- SORU: İstanbul'un ortalama saatlik yolcu profili nedir?
--       Hafta içi ile hafta sonu ritmi nasıl ayrışıyor?
-- Yöntem: Önce gün-saat bazında topla, sonra gün tipine göre ortala
--         (direkt AVG alınsa aylar arası satır sayısı farkı sonucu çarpıtırdı).
-- Kaynak view: yolculuk (kaynak/db.py)

WITH gunluk_saatlik AS (
    SELECT
        transition_date,
        gun_tipi,
        transition_hour,
        SUM(number_of_passenger) AS yolcu
    FROM yolculuk
    GROUP BY 1, 2, 3
)
SELECT
    gun_tipi,
    transition_hour                 AS saat,
    ROUND(AVG(yolcu))               AS ortalama_yolcu
FROM gunluk_saatlik
GROUP BY 1, 2
ORDER BY 1, 2;
