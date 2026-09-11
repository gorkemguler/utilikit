# Araç kataloğu

Registry'den otomatik üretilir. Etkileşimli doküman `/docs` altında; makine
tarafından okunabilir hali `GET /v1/tools`.

**14 araç, 68 endpoint, 8 kategori**


## Kodlama ve şifreleme

### Kodlama, özet (hash) ve JWT

base64/32/hex/url/html/ascii85 kodlama ve çözme, çoklu algoritmalı hash, HMAC, JWT çözme (imza doğrulamadan).

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `POST` | `/v1/encode` | Metni kodla | `{"text":"hello","encoding":"base64"}` |
| `POST` | `/v1/decode` | Metni çöz | `{"text":"aGVsbG8=","encoding":"base64"}` |
| `POST` | `/v1/hash` | Birden çok algoritmayla hashle | `{"text":"hello","algorithms":["sha256","blake2b"]}` |
| `POST` | `/v1/hmac` | HMAC imzala | `{"message":"m","key":"k","algorithm":"sha256"}` |
| `GET` | `/v1/jwt/decode` | Bir JWT'yi çöz | `?token=eyJ...` |


## Üreteçler

### Kimlik ve parola üretici

UUID v1/v4/v7, ULID, Nano ID, rastgele parola ve parola cümlesi, güç tahmini.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/id/uuid` | UUID üret | `?version=7&count=3` |
| `GET` | `/v1/id/ulid` | ULID üret | `?count=3` |
| `POST` | `/v1/id/nanoid` | Nano ID üret | `{"size":12}` |
| `GET` | `/v1/password` | Rastgele parola | `?length=24&symbols=true` |
| `GET` | `/v1/passphrase` | Parola cümlesi | `?words=5` |
| `GET` | `/v1/password/strength` | Güç kontrolü | `?password=hunter2` |


## Medya

### Görsel işleme

Boyutlandırma, dönüştürme ve yeniden sıkıştırma, kare küçük resim, EXIF okuma ve silme, renk paleti, ve tarayıcı gerektirmeyen bir sosyal medya kartı üretici.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `POST` | `/v1/image/transform` | Boyutlandır/dönüştür | `?url=...&width=800&format=webp` |
| `POST` | `/v1/image/thumbnail` | Kare küçük resim | `?url=...&size=256` |
| `POST` | `/v1/image/exif` | EXIF oku | `multipart file=@photo.jpg` |
| `POST` | `/v1/image/strip-exif` | Meta veriyi sil | `multipart file=@photo.jpg` |
| `POST` | `/v1/image/palette` | Baskın renkler | `?url=...` |
| `GET` | `/v1/og-image` | Sosyal medya kartı (PNG) | `?title=Hello&subtitle=World&theme=blue` |

### QR kod ve barkod  _(gerekli: decode (for /v1/qr/decode))_

QR kod (PNG/SVG) ve tek boyutlu barkod üret; bir görselden QR/barkod çöz (opsiyonel ek paket gerekir).

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/qr` | QR kod üret | `?text=https://example.com&format=svg` |
| `POST` | `/v1/qr/decode` | Görselden çöz | `multipart file=@code.png` |
| `GET` | `/v1/barcode` | Barkod üret | `?text=978020137962&symbology=ean13` |


## Ağ ve OSINT

### DNS sorguları

Her tür DNS kaydını çözümle, ters DNS, ve 5 herkese açık resolver üzerinden yayılım kontrolü.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/dns/records` | Bir ad için kayıtlar | `?name=example.com&types=A,MX,TXT` |
| `GET` | `/v1/dns/reverse` | IP için PTR kaydı | `?ip=1.1.1.1` |
| `GET` | `/v1/dns/propagation` | Resolver'ları karşılaştır | `?name=example.com&type=A` |

### HTTP ve TLS incelemesi

Başlıklar ve güvenlik başlığı denetimi, yönlendirme zinciri takibi, TLS sertifika incelemesi, TCP ping ve port kontrolü. Hepsi SSRF korumalı.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/http/headers` | Başlıklar ve süre | `?url=https://example.com` |
| `GET` | `/v1/http/redirects` | Yönlendirme zinciri | `?url=http://google.com` |
| `GET` | `/v1/tls/cert` | TLS sertifikası | `?host=example.com` |
| `GET` | `/v1/net/tcp-ping` | TCP bağlantı gecikmesi | `?host=1.1.1.1&port=443` |
| `GET` | `/v1/net/port-check` | Port kontrolü (küçük) | `?host=example.com&ports=22,80,443` |

### WHOIS / RDAP / ASN  _(gerekli: geo (optional, for /v1/ip/info geo))_

RDAP üzerinden alan adı ve IP kayıt bilgisi (ccTLD'lerde port-43'e düşer), kaynak ASN, ve isteğe bağlı konum bilgisiyle birleşik bir IP dosyası.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/whois/domain` | Alan adı WHOIS | `?domain=example.com` |
| `GET` | `/v1/whois/ip` | IP WHOIS | `?ip=1.1.1.1` |
| `GET` | `/v1/asn` | Kaynak ASN | `?ip=8.8.8.8` |
| `GET` | `/v1/ip/info` | Tam IP dosyası | `?ip=8.8.8.8` |


## Metin ve veri

### JSON / YAML / CSV araçları

JSON biçimlendirme, sıkıştırma ve doğrulama, JSONPath sorguları, YAML↔JSON, CSV↔JSON, sayı tabanı dönüştürme.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `POST` | `/v1/json/format` | JSON biçimlendir | `{"data":"{\"a\":1}"}` |
| `POST` | `/v1/json/query` | JSONPath sorgusu | `{"data":"{\"a\":[1,2]}","path":"$.a[*]"}` |
| `POST` | `/v1/convert/yaml-json` | YAML↔JSON | `{"data":"a: 1","direction":"yaml2json"}` |
| `POST` | `/v1/convert/csv-json` | CSV↔JSON | `{"data":"a,b\n1,2","direction":"csv2json"}` |
| `GET` | `/v1/base/convert` | Taban dönüştür | `?value=255&from_base=10&to_base=16` |

### Metin araçları

slugify, harf durumu dönüşümü, lorem ipsum, unified diff, Markdown→HTML, metin istatistikleri, regex test aracı.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/slugify` | URL slug'ı | `?text=Merhaba Dünya!` |
| `GET` | `/v1/case` | Harf durumunu dönüştür | `?text=helloWorld&to=kebab` |
| `GET` | `/v1/lorem` | Doldurma metni | `?paragraphs=2` |
| `POST` | `/v1/diff` | Unified diff | `{"a":"foo\n","b":"bar\n"}` |
| `POST` | `/v1/markdown` | Markdown'dan HTML'e | `{"text":"# Hi **there**"}` |
| `GET` | `/v1/text/stats` | Metin istatistikleri | `?text=the quick brown fox` |
| `GET` | `/v1/regex/test` | Regex test aracı | `?pattern=\d+&text=a1b22` |


## Zaman ve renk

### Renk araçları

hex/rgb/hsl/hsv arasında dönüştürme, WCAG kontrast oranları, rastgele uyumlu paletler.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/color/convert` | Rengi dönüştür | `?color=%233b82f6` |
| `GET` | `/v1/color/contrast` | Kontrast oranı | `?foreground=%23fff&background=%23555` |
| `GET` | `/v1/color/palette` | Rastgele palet | `?count=5&scheme=analogous` |

### Zaman ve zamanlama

Birçok saat diliminde şu an, zaman damgası ayrıştırma/dönüştürme, cron için sıradaki çalışma zamanları, süreyi okunur hale getirme.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/time/now` | Şu anki zaman | `?timezones=Europe/Istanbul,UTC` |
| `GET` | `/v1/time/convert` | Zaman damgasını dönüştür | `?value=1700000000&to_timezone=Europe/Istanbul` |
| `GET` | `/v1/cron/next` | Cron için sıradaki çalışmalar | `?expression=*/15 * * * *&count=3` |
| `GET` | `/v1/duration/humanize` | Saniyeyi okunur hale getir | `?seconds=93784` |


## Web yakalama

### Ekran görüntüsü ve PDF  _(gerekli: browser)_

Tam sayfa ya da viewport ekran görüntüsü (PNG/JPEG), URL'den PDF, ve ham HTML render. Senkron ya da asenkron (job) modu. 'browser' ek paketini ister.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/screenshot` | Bir URL'nin ekran görüntüsü | `?url=https://example.com&full_page=true&dark=true` |
| `GET` | `/v1/pdf` | URL'den PDF | `?url=https://example.com&paper=A4` |
| `POST` | `/v1/render` | Ham HTML render et | `{"html":"<h1>hi</h1>","as_pdf":true}` |
| `GET` | `/v1/jobs/{id}/result` | Asenkron iş sonucu | `` |


## Web yardımcıları

### Sayfa meta verisi ve çıkarma

Bir URL'nin önizleme verisini çıkar (OG/Twitter/oEmbed/favicon/canonical), ana makale metnini al, linkleri listele ve sınıflandır, HTML'den metne çevir. SSRF korumalı.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/unfurl` | Link önizleme verisi | `?url=https://github.com` |
| `GET` | `/v1/readability` | Ana makale metni | `?url=https://example.com/post&as_markdown=true` |
| `GET` | `/v1/links` | Linkleri çıkar | `?url=https://example.com` |
| `GET` | `/v1/html2text` | HTML'den metne | `?url=https://example.com` |
| `GET` | `/v1/favicon` | En iyi favicon adresi | `?url=https://github.com` |

### Web yardımcıları, request bin ve kısaltıcı

User-Agent çözümleyici, MIME tahmini, Luhn kontrolü, bir webhook request bin'i ve SQLite tabanlı bir URL kısaltıcı.

| Metod | Yol | Ne işe yarar | Örnek |
|---|---|---|---|
| `GET` | `/v1/ua/parse` | User-Agent metnini çözümle | `?user_agent=Mozilla/5.0 ... Chrome/125` |
| `GET` | `/v1/mime` | MIME türünü tahmin et | `?filename=archive.tar.gz` |
| `GET` | `/v1/luhn` | Luhn sağlama toplamı | `?number=4242424242424242` |
| `GET` | `/v1/bin/new` | Yeni request bin | `` |
| `ANY` | `/bin/{id}` | Bir isteği yakala (herkese açık) | `point a webhook here` |
| `GET` | `/v1/bin/{id}` | Yakalanan istekleri listele | `` |
| `POST` | `/v1/short` | Kısa link oluştur | `{"url":"https://example.com/very/long"}` |
| `GET` | `/s/{code}` | Yönlendir (herkese açık) | `` |

