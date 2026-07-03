-- SORU: Kim hangi saatte yolda? Öğrenci, tam bilet, ücretsiz (65+/engelli)
--       şehri aynı saatlerde mi kullanıyor?
-- Yöntem: Her kart grubunun saatlik yolcusunu kendi günlük toplamına oranla
--         (SUM() OVER (PARTITION BY grup)) — gruplar farklı büyüklükte olduğu
--         için mutlak sayı değil "kendi gününün yüzdesi" karşılaştırılır.
-- Not: INDIRIMLI1 ağırlıkla öğrenci; UCRETSIZ 65 yaş üstü ve engelli kartları.

WITH grup_saat AS (
    SELECT
        product_kind          AS kart,
        transition_hour       AS saat,
        SUM(number_of_passenger) AS yolcu
    FROM yolculuk
    WHERE gun_tipi = 'hafta içi'
      AND product_kind IN ('TAM', 'INDIRIMLI1', 'INDIRIMLI2', 'UCRETSIZ')
    GROUP BY 1, 2
)
SELECT
    kart,
    saat,
    yolcu,
    ROUND(100.0 * yolcu / SUM(yolcu) OVER (PARTITION BY kart), 2) AS gun_ici_pay_pct
FROM grup_saat
ORDER BY kart, saat;
