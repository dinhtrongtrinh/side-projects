from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re, time

def click_choice_by_label_and_verify(driver, label_text, timeout=15):
    wait = WebDriverWait(driver, timeout)
    # najdi blok volby podle XPath (používá obsah textu ve vnitřním elementu)
    xpath = (
        f"//div[contains(@class,'survey__answer') and .//div[contains(@class,'survey__progress-text') "
        f"and contains(normalize-space(.), \"{label_text}\")]]"
    )
    # počkej, až se takový blok objeví
    block = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))

    # najdi prvek, který zobrazuje počet hlasů uvnitř tohoto bloku
    try:
        votes_elem = block.find_element(By.CSS_SELECTOR, ".survey__progress-text-result")
        votes_text_before = votes_elem.text  # např. "• 6663 hlasů" nebo "6663 hlasů"
    except:
        votes_text_before = ""

    # pokusíme se z počtu vytáhnout číslo (pokud je tam)
    def extract_num(s):
        m = re.search(r"(\d[\d\s]*)", s)
        if not m:
            return None
        # odstranit mezery a převést na int
        return int(m.group(1).replace(" ", ""))

    num_before = extract_num(votes_text_before)

    # najdi tlačítko a klikni
    btn = block.find_element(By.CSS_SELECTOR, "button.survey__answer-btn")
    # scroll do view pro jistotu, že bude kliknutelné
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    btn.click()

    # po kliknutí čekej na změnu počtu hlasů nebo jiného potvrzení
    # nejprve čekáme krátce na DOM update
    time.sleep(1.0)

    # pokusíme se znovu přečíst počet hlasů a porovnat
    try:
        # kratší čekání - nebo použij WebDriverWait s vlastním expected condition
        votes_elem_after = block.find_element(By.CSS_SELECTOR, ".survey__progress-text-result")
        votes_text_after = votes_elem_after.text
        num_after = extract_num(votes_text_after)
    except Exception as e:
        votes_text_after = None
        num_after = None

    verified = False
    if num_before is not None and num_after is not None:
        verified = (num_after > num_before)
    else:
        # alternativně ověř, zda se objevil např. text "Děkujeme" nebo třída 'voted'
        try:
            # příklad: čekej na změnu třídy tlačítka nebo přítomnost elementu potvrzení
            verified = EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".some-confirmation"), "Děkujeme")(driver)
        except:
            verified = False

    return {
        "before_text": votes_text_before,
        "after_text": votes_text_after,
        "num_before": num_before,
        "num_after": num_after,
        "verified": verified
    }
# Příklad použití:
driver = webdriver.Edge()
driver.get("https://zatecky.denik.cz/volny-cas/anketa-hasici-dobrovolni-sdh-parta-lounsko-zatecko-hlasovani-20251022.html")
res = click_choice_by_label_and_verify(driver, "Vroutek")
print(res)
