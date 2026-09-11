"""Turkish strings for the HTML tool index.

Everything here is optional decoration for ``GET /`` - the API itself has no
notion of language. A small client-side toggle on the page swaps between the
English text baked into the templates and the Turkish text from this module;
nothing here is used outside that one page.

Missing an entry is never fatal: the page falls back to the English string,
so a half-translated new tool still renders fine.
"""

from __future__ import annotations

UI_TR: dict[str, str] = {
    "tagline": "Kendi sunucunda çalışan bir HTTP araç kutusu - {categories} kategoride {tools} araç.",
    "nav_docs": "OpenAPI belgeleri",
    "nav_tools_json": "araç listesi (JSON)",
    "nav_health": "sağlık",
    "nav_metrics": "metrikler",
    "auth_label": "kimlik doğrulama:",
    "auth_required": "X-API-Key gerekli",
    "auth_open": "açık (anahtar yok)",
    "capture_label": "yakalama:",
    "capture_enabled": "etkin",
    "capture_disabled": "kapalı",
    "filter_all": "tümü",
    "needs_label": "gerekli:",
    "try_label": "dene →",
    "example_label": "örn.",
    "footer": "Kendi araçlarını bu sunucuya yönlendir. Makine tarafından okunabilir bir katalog için "
    "GET /v1/tools adresine bak.",
    "quickstart_title": "Kullanım örnekleri",
    "quickstart_sub": "Kopyala, yapıştır, çalıştır. Varsayılanda SDK ya da kimlik doğrulama gerekmiyor.",
    "returns_label": "döner:",
    "qs_whois_title": "Alan adı WHOIS",
    "qs_whois_returns": "kayıt şirketi, tarihler, nameserver'lar, DNSSEC durumu",
    "qs_dns_title": "DNS kayıtları",
    "qs_dns_returns": "istenen tipler için kayıtlar ve TTL değerleri",
    "qs_screenshot_title": "Ekran görüntüsü",
    "qs_screenshot_returns": "tam sayfa PNG, bayt olarak",
    "qs_hash_title": "Çoklu hash",
    "qs_hash_returns": "her algoritma için hesaplanan özet değeri",
    "qs_qr_title": "QR kod",
    "qs_qr_returns": "SVG ya da PNG olarak QR kod görseli",
    "qs_password_title": "Rastgele parola",
    "qs_password_returns": "parola ve tahmini kırılma süresi",
}

CATEGORY_TR: dict[str, str] = {
    "Codecs & crypto": "Kodlama ve şifreleme",
    "Generators": "Üreteçler",
    "Media": "Medya",
    "Network & OSINT": "Ağ ve OSINT",
    "Text & data": "Metin ve veri",
    "Time & colour": "Zaman ve renk",
    "Web capture": "Web yakalama",
    "Web helpers": "Web yardımcıları",
}

TOOL_TR: dict[str, dict[str, str]] = {
    "codec": {
        "title": "Kodlama, özet (hash) ve JWT",
        "description": "base64/32/hex/url/html/ascii85 kodlama ve çözme, çoklu algoritmalı hash, "
        "HMAC, JWT çözme (imza doğrulamadan).",
    },
    "idgen": {
        "title": "Kimlik ve parola üretici",
        "description": "UUID v1/v4/v7, ULID, Nano ID, rastgele parola ve parola cümlesi, güç tahmini.",
    },
    "text": {
        "title": "Metin araçları",
        "description": "slugify, harf durumu dönüşümü, lorem ipsum, unified diff, Markdown→HTML, "
        "metin istatistikleri, regex test aracı.",
    },
    "data_fmt": {
        "title": "JSON / YAML / CSV araçları",
        "description": "JSON biçimlendirme, sıkıştırma ve doğrulama, JSONPath sorguları, YAML↔JSON, "
        "CSV↔JSON, sayı tabanı dönüştürme.",
    },
    "time": {
        "title": "Zaman ve zamanlama",
        "description": "Birçok saat diliminde şu an, zaman damgası ayrıştırma/dönüştürme, cron "
        "için sıradaki çalışma zamanları, süreyi okunur hale getirme.",
    },
    "color": {
        "title": "Renk araçları",
        "description": "hex/rgb/hsl/hsv arasında dönüştürme, WCAG kontrast oranları, rastgele uyumlu paletler.",
    },
    "qr": {
        "title": "QR kod ve barkod",
        "description": "QR kod (PNG/SVG) ve tek boyutlu barkod üret; bir görselden QR/barkod çöz "
        "(opsiyonel ek paket gerekir).",
    },
    "misc": {
        "title": "Web yardımcıları, request bin ve kısaltıcı",
        "description": "User-Agent çözümleyici, MIME tahmini, Luhn kontrolü, bir webhook request bin'i "
        "ve SQLite tabanlı bir URL kısaltıcı.",
    },
    "dns": {
        "title": "DNS sorguları",
        "description": "Her tür DNS kaydını çözümle, ters DNS, ve 5 herkese açık resolver üzerinden yayılım kontrolü.",
    },
    "whois": {
        "title": "WHOIS / RDAP / ASN",
        "description": "RDAP üzerinden alan adı ve IP kayıt bilgisi (ccTLD'lerde port-43'e düşer), "
        "kaynak ASN, ve isteğe bağlı konum bilgisiyle birleşik bir IP dosyası.",
    },
    "net_http": {
        "title": "HTTP ve TLS incelemesi",
        "description": "Başlıklar ve güvenlik başlığı denetimi, yönlendirme zinciri takibi, TLS "
        "sertifika incelemesi, TCP ping ve port kontrolü. Hepsi SSRF korumalı.",
    },
    "web_meta": {
        "title": "Sayfa meta verisi ve çıkarma",
        "description": "Bir URL'nin önizleme verisini çıkar (OG/Twitter/oEmbed/favicon/canonical), "
        "ana makale metnini al, linkleri listele ve sınıflandır, HTML'den metne çevir. SSRF korumalı.",
    },
    "image": {
        "title": "Görsel işleme",
        "description": "Boyutlandırma, dönüştürme ve yeniden sıkıştırma, kare küçük resim, EXIF "
        "okuma ve silme, renk paleti, ve tarayıcı gerektirmeyen bir sosyal medya kartı üretici.",
    },
    "capture": {
        "title": "Ekran görüntüsü ve PDF",
        "description": "Tam sayfa ya da viewport ekran görüntüsü (PNG/JPEG), URL'den PDF, ve ham "
        "HTML render. Senkron ya da asenkron (job) modu. 'browser' ek paketini ister.",
    },
}

# Keyed by the endpoint path (unique across the whole catalogue).
ENDPOINT_TR: dict[str, str] = {
    "/v1/encode": "Metni kodla",
    "/v1/decode": "Metni çöz",
    "/v1/hash": "Birden çok algoritmayla hashle",
    "/v1/hmac": "HMAC imzala",
    "/v1/jwt/decode": "Bir JWT'yi çöz",
    "/v1/id/uuid": "UUID üret",
    "/v1/id/ulid": "ULID üret",
    "/v1/id/nanoid": "Nano ID üret",
    "/v1/password": "Rastgele parola",
    "/v1/passphrase": "Parola cümlesi",
    "/v1/password/strength": "Güç kontrolü",
    "/v1/slugify": "URL slug'ı",
    "/v1/case": "Harf durumunu dönüştür",
    "/v1/lorem": "Doldurma metni",
    "/v1/diff": "Unified diff",
    "/v1/markdown": "Markdown'dan HTML'e",
    "/v1/text/stats": "Metin istatistikleri",
    "/v1/regex/test": "Regex test aracı",
    "/v1/json/format": "JSON biçimlendir",
    "/v1/json/query": "JSONPath sorgusu",
    "/v1/convert/yaml-json": "YAML↔JSON",
    "/v1/convert/csv-json": "CSV↔JSON",
    "/v1/base/convert": "Taban dönüştür",
    "/v1/time/now": "Şu anki zaman",
    "/v1/time/convert": "Zaman damgasını dönüştür",
    "/v1/cron/next": "Cron için sıradaki çalışmalar",
    "/v1/duration/humanize": "Saniyeyi okunur hale getir",
    "/v1/color/convert": "Rengi dönüştür",
    "/v1/color/contrast": "Kontrast oranı",
    "/v1/color/palette": "Rastgele palet",
    "/v1/qr": "QR kod üret",
    "/v1/qr/decode": "Görselden çöz",
    "/v1/barcode": "Barkod üret",
    "/v1/ua/parse": "User-Agent metnini çözümle",
    "/v1/mime": "MIME türünü tahmin et",
    "/v1/luhn": "Luhn sağlama toplamı",
    "/v1/bin/new": "Yeni request bin",
    "/bin/{id}": "Bir isteği yakala (herkese açık)",
    "/v1/bin/{id}": "Yakalanan istekleri listele",
    "/v1/short": "Kısa link oluştur",
    "/s/{code}": "Yönlendir (herkese açık)",
    "/v1/dns/records": "Bir ad için kayıtlar",
    "/v1/dns/reverse": "IP için PTR kaydı",
    "/v1/dns/propagation": "Resolver'ları karşılaştır",
    "/v1/whois/domain": "Alan adı WHOIS",
    "/v1/whois/ip": "IP WHOIS",
    "/v1/asn": "Kaynak ASN",
    "/v1/ip/info": "Tam IP dosyası",
    "/v1/http/headers": "Başlıklar ve süre",
    "/v1/http/redirects": "Yönlendirme zinciri",
    "/v1/tls/cert": "TLS sertifikası",
    "/v1/net/tcp-ping": "TCP bağlantı gecikmesi",
    "/v1/net/port-check": "Port kontrolü (küçük)",
    "/v1/unfurl": "Link önizleme verisi",
    "/v1/readability": "Ana makale metni",
    "/v1/links": "Linkleri çıkar",
    "/v1/html2text": "HTML'den metne",
    "/v1/favicon": "En iyi favicon adresi",
    "/v1/image/transform": "Boyutlandır/dönüştür",
    "/v1/image/thumbnail": "Kare küçük resim",
    "/v1/image/exif": "EXIF oku",
    "/v1/image/strip-exif": "Meta veriyi sil",
    "/v1/image/palette": "Baskın renkler",
    "/v1/og-image": "Sosyal medya kartı (PNG)",
    "/v1/screenshot": "Bir URL'nin ekran görüntüsü",
    "/v1/pdf": "URL'den PDF",
    "/v1/render": "Ham HTML render et",
    "/v1/jobs/{id}/result": "Asenkron iş sonucu",
}
