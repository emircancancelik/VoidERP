# VoidERP: Otonom Finansal Risk ve Likidite Yönetimi Karar Motoru

VoidERP; event-driven (olay güdümlü) mikroservis mimarisi üzerine kurulu, yüksek hacimli finansal işlemleri ve trade sinyallerini asenkron olarak işleyen gerçek zamanlı bir kurumsal karar motorudur. Geleneksel ERP sistemlerinin hantal ve statik veri işleme süreçlerini ekarte ederek, şirketin likidite, nakit akışı ve finansal risk senaryolarını proaktif olarak analiz eder.

## 1. Çekirdek Mimari ve Pod Yapısı

Sistem, Azure Container Apps ve KEDA (Kubernetes Event-driven Autoscaling) dinamiklerine tam uyumlu, scale-to-zero (sıfıra ölçeklenme) yeteneğine sahip bloklamayan (non-blocking) asenkron pod'lardan oluşur:

* **`data_pod`**: SAP BTP ve dış kaynaklı finansal servislerden (veya `sap_mock` servisinden) gelen ham trade sinyallerini ve nakit akış hareketlerini yakalar, yapılandırılmış formata getirerek mesaj kuyruğuna iletir.
* **`rabbitmq`**: Pod'lar arası iletişimi tamamen izole, kayıpsız (durable) ve asenkron hale getiren AMQP broker katmanıdır.
* **`intelligence_pod`**: Kuyruğa düşen trade verilerini Pydantic şemalarıyla anlık doğrular. Hacim ve volatilite tabanlı deterministik risk değerlendirme algoritmalarını çalıştırarak işlemleri `NOMINAL` veya `HIGH_RISK` olarak sınıflandırır.
* **`control_pod` & Dashboard**: Karar motorunun ürettiği risk skorlarını, yaklaşan vadeli yükümlülükleri ve senaryo analizlerini (Cari oran kırılımları, şüpheli alacaklar) asenkron background thread'ler üzerinden Streamlit UI katmanına besler.

## 2. Çözülen Problem ve Gerçek Dünya Senaryosu

### Geleneksel Problem
Geleneksel muhasebe ve ERP yazılımları veriyi geriye dönük işler. Şirketler, nakit akışındaki bir krizi veya likidite darboğazını ancak ödeme günü geldiğinde ya da banka hesabı eksiye düştüğünde fark eder. Ani ve yüksek hacimli bir harcamanın, şirketin önündeki 30 günlük vadeli yükümlülüklerine etkisi anlık olarak hesaplanamaz.

### VoidERP Çözümü (Örnek Senaryo)
Şirket tarafından **340.000 TL** değerinde anlık bir alım emri tetiklendiğinde:
1. `data_pod` işlemi yakalar ve RabbitMQ üzerinden `intelligence_pod`'a fırlatır.
2. `intelligence_pod` işlem hacmini (Volume > 400) analiz ederek saniyeler içinde **`HIGH_RISK`** etiketini basar.
3. Karar motoru, bu harcamanın şirketin yaklaşan kritik ödemelerini (Likidite sağlayıcı teminatları, SAP lisans faturaları) tehlikeye atacağını ve şirketin Cari Oranını (Likidite) **1.42'den ~1.08 seviyesine (güvenli eşik olan 1.2'nin altına)** çekeceğini anlık hesaplar.
4. Dashboard üzerindeki asenkron consumer thread veriyi yakalar, arayüzü kilitlemeden panelde "Yüksek Volatilite Kayması" uyarısı üretir. Yönetim, nakit çıkışı fiilen gerçekleşmeden proaktif önlem alır.

## 3. Teknoloji Yığını (Tech Stack)

* **Dil**: Python 3.14+ (Strict Type Hinting & Pydantic v2 Veri Doğrulaması)
* **Asenkron Altyapı**: `asyncio`, `aio-pika` (Bağlantı kopmalarına karşı `connect_robust` entegrasyonu)
* **Mesajlaşma**: RabbitMQ (Management Alpine)
* **Arayüz**: Streamlit (Session State & Background Worker Thread entegrasyonlu)
* **Konteynerizasyon**: Docker, Docker Compose (Scale-to-zero uyumlu ağ mimarisi)

## 4. Kurulum ve Dağıtım (Deployment)

### Gereksinimler
* Docker ve Docker Compose V2
* Python 3.14+ (Lokal çalıştırma ve testler için)

### Docker Konteynerlerinin Ayağa Kaldırılması

Proje kök dizininde aşağıdaki komutu çalıştırarak tüm pod mimarisini asenkron ağ altyapısıyla birlikte başlatın:

`docker compose up -d --build`
