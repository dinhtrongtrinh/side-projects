# pip install selenium stem webdriver-manager
import socket
import time
import random
import re
from stem import Signal
from stem.control import Controller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --------- NASTAVENÍ (uprav podle potřeby) ---------
TOR_SOCKS = "127.0.0.1:9050"   # lokální Tor SOCKS proxy
TOR_CONTROL_PORT = 9051        # Tor control port
TOR_CONTROL_PASSWORD = None    # pokud máš heslo pro control port, vlož ho sem

TARGET_URL = "https://zatecky.denik.cz/volny-cas/anketa-hasici-dobrovolni-sdh-parta-lounsko-zatecko-hlasovani-20251022.html"
# text volby, kterou chceš hlasovat (přesně nebo jako substring)
OPTION_LABEL = "Vroutek"

ITERATIONS = 10        # kolikrát chceme opakovat celý cyklus
RESTART_EVERY = 1      # restartovat browser každých N iterací (doporučeno 1 nebo 2)
WAIT_FOR_ELEMENT = 15  # max čekání na elementy v sekundách

# uživatelské agenty
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.117 Safari/537.36"
]
def is_tor_ready(host="127.0.0.1", port=9050):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except:
        return False

# --------- FUNKCE PRO TOR NEWNYM (změna IP) ---------
def request_new_tor_identity(password=None):
    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            if password:
                controller.authenticate(password)
            else:
                controller.authenticate()  # cookie auth
            controller.signal(Signal.NEWNYM)
            return True
    except Exception as e:
        print("Chyba při komunikaci s Tor control portem:", e)
        return False

# --------- VYTVOŘENÍ DRIVERU S TOR PROXY ---------
def create_driver(user_agent=None):
    opts = Options()
    # Proxy přes Tor
    opts.add_argument(f'--proxy-server=socks5://{TOR_SOCKS}')
    if user_agent:
        opts.add_argument(f'--user-agent={user_agent}')
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    # odkomentuj, pokud chceš headless: 
    # opts.add_argument("--headless=new")
    # vytvoření driveru (webdriver-manager stáhne vhodný chromedriver)
    # Use Service to pass the chromedriver executable path explicitly and
    # provide options via the options= keyword to avoid positional-arg issues.
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver

# --------- POMOCNÉ FUNKCE ---------
def extract_num(s: str):
    """Z textu vytáhne číslo hlasů (např. '• 6 663 hlasů' -> 6663)"""
    if not s:
        return None
    m = re.search(r"(\d[\d\s]*)", s)
    if not m:
        return None
    return int(m.group(1).replace(" ", ""))

def click_consent_if_present(driver, timeout=3):
    """
    Najde a klikne tlačítko souhlasu (text 'Souhlasím' nebo podobně).
    Vrací True pokud byl consent nalezen a kliknut, jinak False.
    """
    try:
        # XPath hledá button element, který obsahuje text 'Souhlas' (case-sensitive)
        xpath_variants = [
            "//button[normalize-space(.)='Souhlasím']",
            "//button[contains(normalize-space(.), 'Souhlas')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'souhlas')]"
        ]
        for xp in xpath_variants:
            els = driver.find_elements(By.XPATH, xp)
            if els:
                for el in els:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                            time.sleep(0.3)
                            el.click()
                            print("Kliknuto: souhlas (consent).")
                            return True
                    except Exception as e:
                        # ignore a zkusit další element
                        print("Nepodařilo se kliknout na consent tlačítko:", e)
                        continue
        return False
    except Exception as e:
        print("Chyba při hledání consent tlačítka:", e)
        return False

def click_option_by_label(driver, label_text, timeout=WAIT_FOR_ELEMENT):
    """
    Najde div.survey__answer, který obsahuje label_text v pod-elementu survey__progress-text,
    klikne tlačítko uvnitř a vrátí slovník s ověřením.
    """
    wait = WebDriverWait(driver, timeout)
    # XPath: najdi blok, který obsahuje label_text, potom button uvnitř
    xpath_block = (
        f"//div[contains(@class,'survey__answer') and .//div[contains(@class,'survey__progress-text') "
        f"and contains(normalize-space(.), \"{label_text}\")]]"
    )
    try:
        block = wait.until(EC.presence_of_element_located((By.XPATH, xpath_block)))
    except Exception as e:
        print("Blok s volbou nenalezen:", e)
        return {"ok": False, "reason": "block_not_found"}

    # pokus o načtení počtu hlasů před kliknutím
    votes_text_before = ""
    try:
        votes_elem = block.find_element(By.CSS_SELECTOR, ".survey__progress-text-result")
        votes_text_before = votes_elem.text.strip()
    except:
        votes_text_before = ""

    num_before = extract_num(votes_text_before)

    # najdi tlačítko a klikni
    try:
        btn = block.find_element(By.CSS_SELECTOR, "button.survey__answer-btn")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(random.uniform(0.4, 1.2))
        btn.click()
        print("Kliknuto hlasovat pro:", label_text)
    except Exception as e:
        print("Nepodařilo se kliknout na vote button:", e)
        try:
            # fallback přes JS click pokud standardní click selže
            driver.execute_script("arguments[0].click();", btn)
            print("Kliknuto přes JS fallback.")
        except Exception as e2:
            print("Fallback selhal:", e2)
            return {"ok": False, "reason": "click_failed"}

    # počkej chvíli a pokus se zjistit aktualizovaný počet hlasů
    time.sleep(1.0 + random.uniform(0.0, 2.0))
    votes_text_after = ""
    num_after = None
    try:
        votes_elem_after = block.find_element(By.CSS_SELECTOR, ".survey__progress-text-result")
        votes_text_after = votes_elem_after.text.strip()
        num_after = extract_num(votes_text_after)
    except Exception:
        votes_text_after = None
        num_after = None

    verified = False
    if num_before is not None and num_after is not None:
        verified = (num_after > num_before)

    return {
        "ok": True,
        "before_text": votes_text_before,
        "after_text": votes_text_after,
        "num_before": num_before,
        "num_after": num_after,
        "verified": verified
    }

# --------- HLAVNÍ SMYČKA ---------
def main():
    iteration = 0
    driver = None
    try:
        while iteration < ITERATIONS:
            # restart browser každých RESTART_EVERY iterací
            if driver is None or (iteration % RESTART_EVERY == 0 and iteration != 0):
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None

                # požádej Tor o novou IP
                ok = request_new_tor_identity(TOR_CONTROL_PASSWORD)
                if ok:
                    wait_for_tor = 6 + random.uniform(0,4)  # 6-10s
                    print(f"[{iteration}] Požádáno o nový Tor circuit — čekám {wait_for_tor:.1f}s")
                    time.sleep(wait_for_tor)
                else:
                    print("NEWNYM selhal; pokračuji bez změny IP.")

                # čekej až Tor odpoví na socks port před vytvořením driveru
                for attempt in range(8):  # zkusíme 8× (celkem ~16s)
                    if is_tor_ready():
                        break
                    print(f"Čekám na Tor (poke {attempt+1}/8)...")
                    time.sleep(2)
                else:
                    print("Tor se nezdá být dostupný na 127.0.0.1:9050. Spuštění driveru může selhat.")

                ua = random.choice(USER_AGENTS)
                print(f"[{iteration}] Spouštím prohlížeč s UA: {ua}")
                driver = create_driver(user_agent=ua)


            iteration += 1
            print(f"--- Iterace {iteration}/{ITERATIONS} ---")

            # načti stránku
            try:
                driver.set_page_load_timeout(30)
                driver.get(TARGET_URL)
            except Exception as e:
                print("Chyba při načítání stránky:", e)
                # restartuj driver a pokračuj
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                continue

            # 1) kliknout consent/souhlas pokud je zobrazen
            try:
                clicked_consent = click_consent_if_present(driver, timeout=3)
                if clicked_consent:
                    # dej stránce chvíli na aplikování cookie nastavení
                    time.sleep(1.0 + random.uniform(0, 1.5))
            except Exception as e:
                print("Chyba při zpracování consentu:", e)

            # 2) najít volbu a hlasovat
            res = click_option_by_label(driver, OPTION_LABEL, timeout=WAIT_FOR_ELEMENT)
            print("Výsledek hlasování:", res)

            # clean up: smazat cookies a storage (pokud chceme)
            try:
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
            except Exception as e:
                print("Nepodařilo se vyčistit storage/cookies:", e)

            # krátká pauza před dalším cyklem (lidské chování)
            cycle_pause = random.uniform(3.0, 8.0)
            print(f"Čekám {cycle_pause:.1f}s před dalším cyklem.")
            time.sleep(cycle_pause)

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        print("Hotovo.")

if __name__ == "__main__":
    main()
