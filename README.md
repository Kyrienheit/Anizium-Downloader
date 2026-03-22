> [!WARNING]
> İlk açılışta bir kaç dakika bekletebilir, sonrakilerde hızlı açılır.
# Anizium Downloader

Anizium üzerinden dosya indirmeyi sağlayan terminal aracı.

> 
## Özellikler
* Bölüm aralığı verme:
* Altyazıyı ayrı indirme:
* Dublaj dili seçme:

## Kurulum
1. [anizcli.zip](../../releases/latest) dosyasını indirip istediğiniz bir klasöre çıkartın.
2. Klasörün içine girdikten sonra `anizcli.bat` dosyasına çift tıklayarak uygulamayı başlatın. Bu dosya, bilgisayarınızda eksik olan kütüphaneleri (Playwright, yt-dlp vb.) otomatik olarak kuracak ve ardından programı başlatacaktır.
3. Sadece ilk çalıştırmada Anizium hesabınızın kullanıcı adı ve şifresini soracak.  
   Terminalde girmek istemiyorsanız `config.json` içinden tırnakların içine bilgilerinizi girebilirsiniz.

### Kaynak Koddan Çalıştırma
```bash
git clone [https://github.com/Kyrienheit/anizium-downloader.git](https://github.com/Kyrienheit/anizium-downloader.git)
cd anizium-downloader

pip install -r requirements.txt

playwright install chromium

python anizium.py
```

## Kullanım
> [!NOTE]
> Belli aralıktaki bölümleri seçmek için:
>
| Giriş  | Sonuç |
| ------------- | ------------- |
| 2 | Sadece 2. Bölüm  |
| 2-5 | 2,3,4,5. Bölümler |
| 1,3,7 | 1, 3 ve 7. Bölümler |
| all | O sezondaki tüm bölümler |

> [!NOTE]
> Varsayılan indirilenler klasörü anizcli klasörünün içinde. Kendi klasör dizininizi vermek için:  
> `config.json` içindeki **download_path** değerini dosya dizini olarak değşitirin.
>   
> Örnek dosya:
```json
{
    "username": "user123",
    "password": "sifre123",
    "user_token": "boşbırak",
    "download_path": ""C:\\Users\\Admin\\Videos\\Anime""
}
```

### Gereksinimler
Bu proje arka planda aşağıdaki kütüphane ve araçları kullanmaktadır:

- playwright

- yt-dlp

- requests

### SSS
- "Timeout 10000ms exceeded" hatası alıyorum. - İnternet kesilmiştir veya siteye güncelleme gelmiştir de ben güncellememişimdir.

- Program indirmeye başlamadan kapanıyor. - Üyeliğiniz dolmuş ya da şifreniz değişmiş olabilir. Klasördeki config.json dosyasını silip programı tekrar başlatın ve güncel bilgilerinizi girin.

- İndirme çok yavaş. - Bende hızlı.

### Disclaimer
Bu araç tamamen kişisel kullanım ve eğitim amaçlı geliştirilmiş bir web-scraping (veri kazıma) projesidir. Yazılım, herhangi bir video dosyasını barındırmaz, sunmaz veya dağıtmaz; sadece kullanıcının tarayıcısında yapabileceği işlemleri otomatikleştirir.

İndirilen tüm içeriklerin telif hakları ilgili yayıncılara ve platformlara aittir. Geliştirici, bu aracın kullanımından doğabilecek hiçbir yasal sorumluluğu kabul etmez. Lütfen yerel telif hakkı yasalarına uyunuz.
