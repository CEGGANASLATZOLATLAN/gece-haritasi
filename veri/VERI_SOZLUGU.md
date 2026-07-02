# Veri Sözlüğü — Saatlik Toplu Ulaşım Veri Seti

Kaynak: [İBB Açık Veri — Saatlik Toplu Ulaşım Veri Seti](https://data.ibb.gov.tr/dataset/hourly-public-transport-data-set) (BELBİM A.Ş.)
İncelenen dosya: `hourly_transportation_202410.csv` (Ekim 2024). Detaylı otopsi: `defterler/01_otopsi.ipynb`

## Kolonlar

| Kolon | Tip | Açıklama | Dikkat |
|-------|-----|----------|--------|
| `transition_date` | DATE | Yolculuk günü (ISO: `2024-10-01`) | Ay dosyası eksik günler içerebilir — önce validate! |
| `transition_hour` | VARCHAR | Saat dilimi, `"00"`–`"23"` | String gelir, sıfır dolgulu; sayısal işlem için CAST gerekir |
| `transport_type_id` | INT | 1=OTOYOL, 2=RAYLI, 3=DENİZ | `road_type` ile bire bir |
| `road_type` | VARCHAR | Ulaşım türü adı | `DENİZ` Türkçe karakter içerir (İ) — filtre yazarken kopyala-yapıştır |
| `line` | VARCHAR | Hat güzergâh açıklaması (uzun ad) | Serbest metin, tutarsız boşluk/tire olabilir |
| `transfer_type` | VARCHAR | `Normal` / `Aktarma` | |
| `number_of_passage` | INT | Turnike/validatör geçiş sayısı | Toplamı yolcudan ~%2,6 fazla |
| `number_of_passenger` | INT | Yolcu (kişi) sayısı | **Analizlerde bu kullanılır** |
| `product_kind` | VARCHAR | Kart tipi: TAM, INDIRIMLI1, INDIRIMLI2, UCRETSIZ... | |
| `transaction_type_desc` | VARCHAR | İşlem açıklaması (Tam Kontur, Indirimli Aktarma...) | |
| `town` | VARCHAR | İlçe (39 değer + NULL) | **Türe göre anlamı değişir — aşağıya bak** |
| `line_name` | VARCHAR | Kısa hat kodu (25G, M2, TM10...) | |
| `station_poi_desc_cd` | VARCHAR | İstasyon/iskele adı | Otobüste ~%92 boş |

## Kritik tuzaklar

1. **Eksik ay dosyaları:** Ekim 2024 dosyası portalda eksik — sadece 5 tam gün
   (2, 4, 16, 17, 18 Ekim) içeriyor; kalan günlerde neredeyse yalnız `00` saati var.
   İndirme hatası değil, kaynak dosya böyle (CKAN API boyutuyla bayt bayt doğrulandı).
   → Her dosya kullanılmadan önce `scriptler/validate_csv.py` ile kontrol edilir.
2. **`town` iki anlamlı:**
   - RAYLI → istasyonun gerçek ilçesi ✅ (coğrafi analizde kullanılabilir)
   - OTOYOL → hattın sabit işletme/garaj bölgesi ❌ (BAKIRKOY'un anormal payı bundan;
     ilçe analizinde kullanma)
   - M7 metrosunda tamamen NULL (~1.2M yolcu) → `veri/esleme/` altında elle eşleme gerekir.
3. **Granülarite türe göre değişir:** RAYLI=istasyon, OTOYOL=hat, DENİZ=iskele.
4. **Metin alanları transliterasyonlu BÜYÜK HARF** (USKUDAR, KAGITHANE) — tek istisna
   `road_type='DENİZ'`.

## Ölçek (tam bir gün için referans)

- Tam gün ≈ 550 bin satır, ~7.5M yolcu/gün civarı
- Tam ay ≈ ~17M satır bekle (~1.6 GB CSV) → pandas'a yükleme, DuckDB'de işle
