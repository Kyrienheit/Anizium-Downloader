import os
import logging
import re
from playwright.sync_api import sync_playwright

# Windows terminali ANSI renk destekle
os.system("")
C  = "\033[96m"   # Cyan  – başlıklar
Y  = "\033[93m"   # Yellow – listeler
G  = "\033[92m"   # Green  – bilgi/otomatik
R  = "\033[0m"    # Reset
B  = "\033[1m"    # Bold

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("anizium_debug.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def main():
    print(f"{B}{C}=== Anizium Downloader ==={R}")
    anime_name = input(f"{Y}İndirmek istediğiniz anime adı: {R}")
    
    # Yapılandırma dosyasını yükle veya oluştur
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            import json
            config = json.load(f)
    else:
        print("Giriş bilgilerinizi girin:")
        import json
        config = {
            "username": input(f"{Y}Anizium Kullanıcı Adı: {R}"),
            "password": input(f"{Y}Şifre: {R}"),
            "user_token": input(f"{Y}User Token (isteğe bağlı, boş bırakılabilir): {R}")
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
    user_token = config.get("user_token", "") 
    username_str = config.get("username", "")
    password_str = config.get("password", "")
    download_path = config.get("download_path", "") or "indirilenler"

    # download_path config'de yoksa ekle ve kaydet
    if "download_path" not in config:
        config["download_path"] = download_path
        import json as _j
        with open(config_file, "w", encoding="utf-8") as f:
            _j.dump(config, f, indent=4)

    # Klasör yoksa oluştur
    os.makedirs(download_path, exist_ok=True)

    # Kullanıcı adı veya şifre boşsa sor ve kaydet
    changed = False
    if not username_str:
        username_str = input(f"{Y}Anizium kullanıcı adı: {R}").strip()
        config["username"] = username_str
        changed = True
    if not password_str:
        password_str = input(f"{Y}Şifre: {R}").strip()
        config["password"] = password_str
        changed = True
    if changed:
        with open(config_file, "w", encoding="utf-8") as f:
            import json as _json
            _json.dump(config, f, indent=4)
        print("[INFO] Bilgiler kaydedildi.\n")

    
    with sync_playwright() as p:
        logging.info("Playwright başlatılıyor...")
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            extra_http_headers={"Referer": "https://anizium.co/", "Origin": "https://anizium.co"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 1. SİTEYE GİRİŞ YAPMA (LOGIN)
        #logging.info("Hesaba giriş yapılıyor...")
        try:
            page.goto("https://anizium.co/login")
            page.wait_for_load_state("networkidle")
            
            # Direkt formun içindeki inputları hedefliyoruz
            page.locator('#value').fill(username_str)
            page.locator('#password').fill(password_str)
            
            # Formun içindeki butona tıkla
            page.locator('#loginSubmit').click()
            
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(3000) # Bekleyip ekran görüntüsü alalım
            page.screenshot(path="post_login.png")
            #logging.info(f"Oturum açma denendi. Mevcut URL: {page.url}")
            
            if "profiles" in page.url:
                #logging.info("Profil ekranı algılandı. HTML kaydediliyor ve ilk profile tıklanıyor...")
                with open("profiles_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                
                # Try to click the first profile image/link (ignoring "Profil Oluştur" button)
                # Genellikle profil seçimi a etiketleri içindedir
                try:
                    page.evaluate('''() => {
                        let profiles = Array.from(document.querySelectorAll('a')).filter(a => a.href.includes('/set-profile') || a.href.includes('profile_id'));
                        if(profiles.length > 0) profiles[0].click();
                        else {
                            // yedek olarak, içinde img olan ilk linke tıkla (header hariç)
                            let imgs = document.querySelectorAll('div#content a img');
                            if(imgs.length > 0) imgs[0].closest('a').click();
                        }
                    }''')
                    page.wait_for_load_state("networkidle", timeout=15000)
                    #logging.info("Profile tıklandı.")
                except Exception as ex:
                    logging.error(f"Profile tıklanırken hata: {ex}")
        except Exception as e:
            logging.error(f"Giriş başarısız. Hata: {e}")
            browser.close()
            return

        # User token henüz yoksa, bir watch sayfasını ziyaret edip embed URL'den çek
        if not user_token:
            #logging.info("[INFO] Kullanıcı tokeni alınıyor...")
            print("[INFO] Token alınıyor...")
            captured_token = []
            def grab_token(req):
                if "x.anizium.co/embed" in req.url:
                    import urllib.parse
                    params = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
                    if "u" in params and params["u"][0]:
                        captured_token.append(params["u"][0])
            page.on("request", grab_token)
            try:
                page.goto("https://anizium.co/watch/202849446?season=1&episode=1", wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(5000)
            except:
                pass
            page.remove_listener("request", grab_token)
            if captured_token:
                user_token = captured_token[0]
                config["user_token"] = user_token
                import json as _json
                with open(config_file, "w", encoding="utf-8") as f:
                    _json.dump(config, f, indent=4)
                print(f"[INFO] Token kaydedildi.\n")
            else:
                logging.error("Token alınamadı. Lütfen config.json dosyasına user_token'ı manuel olarak girin.")
                browser.close()
                return

        # 2. ARAMA VE ID BULMA
        logging.info(f"'{anime_name}' aranıyor...")
        search_api_results = []
        
        def handle_search_api(res):
            try:
                if "search" in res.url and res.request.method == "GET":
                    data = res.json()
                    if "page" in data and "data" in data["page"] and isinstance(data["page"]["data"], list):
                        search_api_results.extend(data["page"]["data"])
                    elif "data" in data and isinstance(data["data"], list):
                        search_api_results.extend(data["data"])
            except:
                pass

        page.on("response", handle_search_api)
        page.goto(f"https://anizium.co/search?value={anime_name}", wait_until="networkidle")
        
        try:
            page.wait_for_selector('a[href^="/anime/"]', timeout=10000)
            page.remove_listener("response", handle_search_api)
            
            unique_animes_dict = {}
            for item in search_api_results:
                aid = item.get("ID")
                name = item.get("name")
                atype = item.get("type", "series")
                if aid and name and aid not in unique_animes_dict:
                    unique_animes_dict[aid] = {"title": name, "type": atype}
                    
            unique_animes = [{"ID": k, "title": v["title"], "type": v["type"]} for k, v in unique_animes_dict.items()]
            
            if not unique_animes:
                logging.warning("API'den isimler alınamadı, DOM'dan fallback uygulanıyor...")
                fallback_results = page.evaluate('''() => {
                    let links = Array.from(document.querySelectorAll('a[href^="/anime/"]'));
                    return links.map(a => a.getAttribute('href').split('/').pop().split('?')[0]);
                }''')
                
                seen = set()
                for aid in fallback_results:
                    if aid and aid not in seen:
                        seen.add(aid)
                        # Try to get title from DOM if API fails
                        title = page.evaluate(f'() => {{ let a = document.querySelector(\'a[href*="{aid}"]\'); return a ? a.innerText.split("\\n")[0].trim() : "Bilinmeyen Anime (ID: {aid})"; }}')
                        unique_animes.append({"ID": aid, "title": title, "type": "series"})

                if not unique_animes:
                    logging.error("Arama sonucu okunamadı veya liste boş.")
                    browser.close()
                    return

            print(f"\n{B}{C}=== '{anime_name}' İçin Arama Sonuçları ==={R}")
            for idx, anime in enumerate(unique_animes, 1):
                print(f"{Y}{idx}: {anime['title']}{R}")

            if len(unique_animes) == 1:
                secilen_anime = unique_animes[0]
                print(f"{G}[INFO] Tek sonuç, otomatik seçildi: {secilen_anime['title']}{R}")
            else:
                secim = input(f"{Y}\nAnime seç: (1-{len(unique_animes)}): {R}").strip()
                try:
                    secim_idx = int(secim)
                    if 1 <= secim_idx <= len(unique_animes):
                        secilen_anime = unique_animes[secim_idx - 1]
                    else:
                        secilen_anime = unique_animes[0]
                except ValueError:
                    secilen_anime = unique_animes[0]
                
            anime_id = secilen_anime['ID']
            anime_name = secilen_anime['title']
            anime_type = secilen_anime['type']
            logging.info(f"Seçildi: {anime_name} (ID: {anime_id}, Type: {anime_type})")
            
        except Exception as e:
            logging.error(f"Anime bulunamadı. Hata: {str(e)}")
            browser.close()
            return

        # 3. BÖLÜM LİSTESİNİ ÇEKME (Sadece Seri ise)
        is_movie = (anime_type == "movie")
        
        if not is_movie:
            watch_url = f"https://anizium.co/watch/{anime_id}?season=1&episode=1&u={user_token}"
            logging.info("Bölümler çekiliyor...")
            page.goto(watch_url)
            
            try:
                page.wait_for_selector("#episode_table", timeout=15000)
                seasons_data = page.evaluate('''() => {
                    let data = {};
                    document.querySelectorAll('div#episode_table').forEach(table => {
                        let season = table.getAttribute('data-season');
                        let episodes = table.querySelectorAll('a').length;
                        if(episodes > 0) {
                            data[season] = episodes;
                        }
                    });
                    return data;
                }''')
            except Exception as e:
                with open("error_watch_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                logging.error(f"Bölüm listesi çekilemedi. Klasördeki 'error_watch_page.html' dosyasına bak. Hata: {e}")
                browser.close()
                return

            if not seasons_data:
                logging.error("Hiçbir sezon veya bölüm bulunamadı.")
                browser.close()
                return

            print(f"\n{B}{C}=== Mevcut Sezonlar ==={R}")
            for s, ep_count in seasons_data.items():
                print(f"{Y}Sezon {s}: Toplam {ep_count} Bölüm{R}")

            if len(seasons_data) == 1:
                secilen_sezon = list(seasons_data.keys())[0]
                print(f"{G}[INFO] Tek sezon, otomatik seçildi: Sezon {secilen_sezon}{R}")
            else:
                secilen_sezon = input(f"{Y}\nSezon seç: {R}")
                if secilen_sezon not in seasons_data:
                    logging.error("Geçersiz sezon numarası.")
                    browser.close()
                    return
                
            max_ep = seasons_data[secilen_sezon]
            secilen_bolum = input(f"{Y}Bölüm seç: {R}").strip()
            
            episodes_to_download = []
            if secilen_bolum.lower() == 'all':
                episodes_to_download = list(range(1, int(max_ep) + 1))
            elif '-' in secilen_bolum and ',' not in secilen_bolum:
                parts = secilen_bolum.split('-')
                episodes_to_download = list(range(int(parts[0]), int(parts[1]) + 1))
            elif ',' in secilen_bolum:
                episodes_to_download = [int(x.strip()) for x in secilen_bolum.split(',') if x.strip().isdigit()]
            else:
                episodes_to_download = [int(secilen_bolum)]
            
            start_ep = episodes_to_download[0]
            end_ep = episodes_to_download[-1]
        else:
            # Film ise varsayılan değerler
            secilen_sezon = "1"
            start_ep = 1
            end_ep = 1
            logging.info("Film algılandı, bölüm seçimi atlanıyor.")

        # Film için episodes_to_download set edilmemişti, şimdi set ediyoruz
        if is_movie:
            episodes_to_download = [1]

        # ─────────────────────────────────────────────────────────────────────
        # Yardımcı: /anime/source API'sini doğrudan çağır, JSON döndür
        # ─────────────────────────────────────────────────────────────────────
        def fetch_source(ep_no):
            """
            İlgili bölümün kaynak verisini döndürür: {"success":true/false, "subtitles":[], "groups":[]}
            Başarısız/hata durumunda None döner.
            """
            api_url = (
                f"https://api.anizium.co/anime/source"
                f"?id={anime_id}&season={secilen_sezon}&episode={ep_no}"
                f"&server=1&plan=lite&u={user_token}&lang=tr"
            )
            captured = [None]

            def on_res(res):
                if "anime/source" in res.url:
                    try:
                        captured[0] = res.json()
                    except:
                        pass

            embed_url = (
                f"https://x.anizium.co/embed?u={user_token}"
                f"&site=main&lang=tr&id={anime_id}"
                f"&plan=lite&server=1&skin=beta&season={secilen_sezon}&episode={ep_no}"
            )
            try:
                page.on("response", on_res)
                page.goto(embed_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(6000)
                page.remove_listener("response", on_res)
            except:
                try:
                    page.remove_listener("response", on_res)
                except:
                    pass
            return captured[0]

        # ─────────────────────────────────────────────────────────────────────
        # Probe: ilk bölümden dub ve altyazı seçeneklerini öğren
        # ─────────────────────────────────────────────────────────────────────
        print("\n[INFO] Mevcut diller ve altyazılar kontrol ediliyor...")
        first_ep = episodes_to_download[0]
        probe_data = fetch_source(first_ep)

        if probe_data and probe_data.get("success"):
            groups    = probe_data.get("groups", [])      # dublaj seçenekleri
            subtitles = probe_data.get("subtitles", [])   # altyazı seçenekleri
        else:
            err_msg = probe_data.get("msg", "Bilinmeyen hata") if probe_data else "API yanıt vermedi"
            logging.warning(f"İlk bölüm kaynak verisi alınamadı: {err_msg}")
            groups    = []
            subtitles = []

        # ── Dublaj dili seçimi ────────────────────────────────────────────────
        chosen_group = None   # {"group": "original", "name": "Japonca", "items": [...]}

        if not groups:
            # groups boş — bölüm bakımda vs. yine de devam etmeyi dene
            logging.warning("Hiçbir dublaj grubu bulunamadı. Varsayılan olarak 'original' kullanılacak.")
            chosen_dil_eki = "original"
        elif len(groups) == 1:
            chosen_group = groups[0]
            chosen_dil_eki = chosen_group["group"]
            print(f"{G}\n[INFO] Tek ses seçeneği, otomatik seçildi: {chosen_group['name']}{R}")

        else:
            print(f"\n{B}{C}=== Mevcut Ses/Dublaj Seçenekleri ==={R}")
            for i, g in enumerate(groups, 1):
                print(f"{Y}{i}: {g['name']}{R}")
            while True:
                dil_sec = input(f"{Y}\nSes seç (1-{len(groups)}): {R}").strip()
                try:
                    dil_idx = int(dil_sec)
                    if 1 <= dil_idx <= len(groups):
                        chosen_group = groups[dil_idx - 1]
                        chosen_dil_eki = chosen_group["group"]
                        break
                    else:
                        print("Geçersiz seçim, tekrar deneyin.")
                except ValueError:
                    print("Lütfen bir sayı girin.")

        # ── Kalite seçimi (720p varsayılan) ──────────────────────────────────
        chosen_quality = 720   # yt-dlp zaten en iyiyi seçer ama biz de saklayalım

        # ── Altyazı dili seçimi ───────────────────────────────────────────────
        chosen_sub_group = None   # {"group": "tr", "name": "Türkçe", "link": "..."}

        if not subtitles:
            logging.warning("Bu bölüm için altyazı bulunamadı.")
        elif len(subtitles) == 1:
            chosen_sub_group = subtitles[0]
            print(f"{G}\n[INFO] Tek altyazı seçeneği, otomatik seçildi: {chosen_sub_group['name']}{R}")
        else:
            print(f"\n{B}{C}=== Mevcut Altyazı Dilleri ==={R}")
            for i, s in enumerate(subtitles, 1):
                print(f"{Y}{i}: {s['name']} [{s['group']}]{R}")
            while True:
                sub_sec = input(f"{Y}\nAltyazı dili seç (1-{len(subtitles)}): {R}").strip()
                try:
                    sub_idx = int(sub_sec)
                    if 1 <= sub_idx <= len(subtitles):
                        chosen_sub_group = subtitles[sub_idx - 1]
                        break
                    else:
                        print("Geçersiz seçim, tekrar deneyin.")
                except ValueError:
                    print("Lütfen bir sayı girin.")
            logging.info(f"Seçilen altyazı: {chosen_sub_group}")

        # ─────────────────────────────────────────────────────────────────────
        # 4. İNDİRME DÖNGÜSÜ
        # ─────────────────────────────────────────────────────────────────────
        print("\n")

        for ep in episodes_to_download:
            label = f"Film" if is_movie else f"S{int(secilen_sezon):02d}E{ep:02d}"
            logging.info(f"{label} indiriliyor...")

            # İlk bölüm için probe verisini yeniden kullan, diğerleri için API çağır
            if ep == first_ep and probe_data:
                src_data = probe_data
            else:
                src_data = fetch_source(ep)

            if not src_data:
                logging.error(f"{label} atlandı: API yanıt vermedi.")
                continue

            if not src_data.get("success", False):
                msg = src_data.get("msg", "Bilinmeyen hata")[:120]
                logging.warning(f"{label} atlandı: {msg}")
                continue

            ep_groups    = src_data.get("groups", [])
            ep_subtitles = src_data.get("subtitles", [])

            # Seçilen dublaj grubunu bu bölümde bul
            ep_group = next(
                (g for g in ep_groups if g["group"] == chosen_dil_eki),
                ep_groups[0] if ep_groups else None
            )

            if not ep_group:
                logging.warning(f"{label} için '{chosen_dil_eki}' ses grubu bulunamadı, atlanıyor.")
                continue

            # En yüksek kaliteyi seç
            items = ep_group.get("items", [])
            best_item = max(items, key=lambda x: x.get("quality", 0)) if items else None
            if not best_item:
                logging.warning(f"{label} için video linki bulunamadı.")
                continue

            video_url = best_item["link"]
            safe_name = "".join([c for c in anime_name if c.isalnum() or c in (" ", "-", "_")]).replace(" ", "_")

            if is_movie:
                file_name = os.path.join(download_path, f"{safe_name}_film_{chosen_dil_eki}.mp4")
            else:
                file_name = os.path.join(download_path, f"{safe_name}_S{int(secilen_sezon):02d}E{ep:02d}_{chosen_dil_eki}.mp4")

            logging.info(f"Video URL: {video_url}")
            logging.info(f"Dosya: {file_name}")
            os.system(f'python -m yt_dlp "{video_url}" -o "{file_name}"')

            # Altyazı indir
            if ep_subtitles and chosen_sub_group:
                # Seçilen dil bu bölümde mevcut mu kontrol et
                ep_sub = next(
                    (s for s in ep_subtitles if s["group"] == chosen_sub_group["group"]),
                    ep_subtitles[0]   # yoksa ilki
                )
                sub_url = ep_sub["link"]
                sub_file_name = file_name.replace(".mp4", ".vtt")
                logging.info(f"Altyazı: {sub_url}")
                try:
                    response = page.request.get(sub_url)
                    if response.ok:
                        with open(sub_file_name, "wb") as sf:
                            sf.write(response.body())
                        logging.info(f"Altyazı indirildi: {sub_file_name}")
                    else:
                        logging.error(f"Altyazı indirilemedi: HTTP {response.status}")
                except Exception as sub_err:
                    logging.error(f"Altyazı indirilemedi: {sub_err}")
            elif not ep_subtitles:
                logging.info(f"{label} için altyazı mevcut değil.")

        browser.close()
        logging.info("Tüm işlemler tamamlandı.")

if __name__ == "__main__":
    main()
