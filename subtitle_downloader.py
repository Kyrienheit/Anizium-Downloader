import os
import logging
import re
import json
from playwright.sync_api import sync_playwright

# Windows terminali ANSI renk destekle
os.system("")
C  = "\033[96m"   # Cyan  – başlıklar
Y  = "\033[93m"   # Yellow – listeler / promptlar
G  = "\033[92m"   # Green  – bilgi/otomatik
R  = "\033[0m"    # Reset
B  = "\033[1m"    # Bold

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("altyazi_debug.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def main():
    print(f"{B}{C}=== Anizium Altyazı İndirici ==={R}")
    anime_name = input(f"{Y}İndirmek istediğiniz anime adı: {R}")

    # Yapılandırma dosyasını yükle veya oluştur
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        print("Giriş bilgilerinizi girin:")
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

    if "download_path" not in config:
        config["download_path"] = download_path
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    os.makedirs(download_path, exist_ok=True)

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
            json.dump(config, f, indent=4)
        print("[INFO] Bilgiler kaydedildi.\n")

    with sync_playwright() as p:
        logging.info("Playwright başlatılıyor...")
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            extra_http_headers={"Referer": "https://anizium.co/", "Origin": "https://anizium.co"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 1. GİRİŞ
        try:
            page.goto("https://anizium.co/login")
            page.wait_for_load_state("networkidle")
            page.locator('#value').fill(username_str)
            page.locator('#password').fill(password_str)
            page.locator('#loginSubmit').click()
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(3000)

            if "profiles" in page.url:
                with open("profiles_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                try:
                    page.evaluate('''() => {
                        let profiles = Array.from(document.querySelectorAll('a')).filter(a => a.href.includes('/set-profile') || a.href.includes('profile_id'));
                        if(profiles.length > 0) profiles[0].click();
                        else {
                            let imgs = document.querySelectorAll('div#content a img');
                            if(imgs.length > 0) imgs[0].closest('a').click();
                        }
                    }''')
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception as ex:
                    logging.error(f"Profile tıklanırken hata: {ex}")
        except Exception as e:
            logging.error(f"Giriş başarısız. Hata: {e}")
            browser.close()
            return

        # Token alma
        if not user_token:
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
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
                print("[INFO] Token kaydedildi.\n")
            else:
                logging.error("Token alınamadı. Lütfen config.json dosyasına user_token'ı manuel olarak girin.")
                browser.close()
                return

        # 2. ARAMA
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

        # 3. BÖLÜM LİSTESİ
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
                logging.error(f"Bölüm listesi çekilemedi. Hata: {e}")
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
        else:
            secilen_sezon = "1"
            start_ep = 1
            episodes_to_download = [1]
            logging.info("Film algılandı, bölüm seçimi atlanıyor.")

        # 4. ALTYAZI İNDİRME DÖNGÜSÜ
        print("\n")

        # ─────────────────────────────────────────────────────────────────────
        # Yardımcı: /anime/source API'sini embed üzerinden yakala
        # ─────────────────────────────────────────────────────────────────────
        def fetch_source(ep_no):
            captured = [None]

            def on_res(res):
                if "anime/source" in res.url:
                    try:
                        captured[0] = res.json()
                    except:
                        pass

            if is_movie:
                embed_url = (
                    f"https://x.anizium.co/embed?u={user_token}"
                    f"&site=main&lang=tr&id={anime_id}"
                    f"&plan=lite&server=2&skin=art"
                )
            else:
                embed_url = (
                    f"https://x.anizium.co/embed?u={user_token}"
                    f"&site=main&lang=tr&id={anime_id}"
                    f"&plan=lite&server=1&skin=beta"
                    f"&season={secilen_sezon}&episode={ep_no}"
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
        # Probe: ilk bölümden altyazı seçeneklerini öğren
        # ─────────────────────────────────────────────────────────────────────
        first_ep = episodes_to_download[0]
        logging.info(f"Mevcut altyazı dilleri kontrol ediliyor (bölüm {first_ep})...")
        probe_data = fetch_source(first_ep)

        if probe_data and probe_data.get("success"):
            probe_subtitles = probe_data.get("subtitles", [])
        else:
            err_msg = probe_data.get("msg", "Bilinmeyen hata") if probe_data else "API yanıt vermedi"
            logging.warning(f"İlk bölüm kaynak verisi alınamadı: {err_msg}")
            probe_subtitles = []

        # ── Altyazı dili seçimi ───────────────────────────────────────────────
        chosen_sub = None   # {"group": "tr", "name": "Türkçe", "link": "..."}

        if not probe_subtitles:
            logging.warning("Bu bölüm/anime için altyazı bulunamadı.")
        elif len(probe_subtitles) == 1:
            chosen_sub = probe_subtitles[0]
            print(f"{G}\n[INFO] Tek altyazı seçeneği, otomatik seçildi: {chosen_sub['name']}{R}")
        else:
            print(f"\n{B}{C}=== Mevcut Altyazı Dilleri ==={R}")
            for i, s in enumerate(probe_subtitles, 1):
                print(f"{Y}{i}: {s['name']} [{s['group']}]{R}")
            while True:
                sub_sec = input(f"{Y}\nAltyazı dili seç (1-{len(probe_subtitles)}): {R}").strip()
                try:
                    sub_idx = int(sub_sec)
                    if 1 <= sub_idx <= len(probe_subtitles):
                        chosen_sub = probe_subtitles[sub_idx - 1]
                        break
                    else:
                        print("Geçersiz seçim, tekrar deneyin.")
                except ValueError:
                    print("Lütfen bir sayı girin.")
            logging.info(f"Seçilen altyazı: {chosen_sub}")

        # ─────────────────────────────────────────────────────────────────────
        # Bölüm döngüsü
        # ─────────────────────────────────────────────────────────────────────
        for ep in episodes_to_download:
            label = "Film" if is_movie else f"S{int(secilen_sezon):02d}E{ep:02d}"
            logging.info(f"{label} altyazısı indiriliyor...")

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

            ep_subtitles = src_data.get("subtitles", [])
            if not ep_subtitles:
                logging.warning(f"{label} için altyazı bulunamadı.")
                continue

            # Seçilen dili bu bölüm için bul
            if chosen_sub:
                ep_sub = next(
                    (s for s in ep_subtitles if s["group"] == chosen_sub["group"]),
                    ep_subtitles[0]
                )
            else:
                ep_sub = ep_subtitles[0]

            sub_url = ep_sub["link"]
            safe_name = "".join([c for c in anime_name if c.isalnum() or c in (" ", "-", "_")]).replace(" ", "_")

            if is_movie:
                sub_file_name = os.path.join(download_path, f"{safe_name}_film.vtt")
            else:
                sub_file_name = os.path.join(download_path, f"{safe_name}_S{int(secilen_sezon):02d}E{ep:02d}.vtt")

            logging.info(f"Altyazı URL: {sub_url}")
            try:
                response = page.request.get(sub_url)
                if response.ok:
                    with open(sub_file_name, "wb") as sf:
                        sf.write(response.body())
                    logging.info(f"Altyazı indirildi: {sub_file_name}")
                else:
                    logging.error(f"Altyazı indirilemedi: HTTP {response.status}")
            except Exception as dl_err:
                logging.error(f"Altyazı indirilemedi: {dl_err}")

        browser.close()
        logging.info("Tüm altyazı işlemleri tamamlandı.")

if __name__ == "__main__":
    main()
