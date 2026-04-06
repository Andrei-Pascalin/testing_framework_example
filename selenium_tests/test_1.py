from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
from utils.test_results_sender import SendingManager

msg_manager = SendingManager()

driver = webdriver.Chrome()

result_state = False
result_msg = ""

try:
    driver.get("https://www.rustic-handmade.ro")
    wait = WebDriverWait(driver, 10)
    contact = wait.until(
        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Contact"))
    )
    contact.click()
    contact_text_element = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    # Get all visible text from the page
    text = contact_text_element.text
    # text_list = text.splitlines()
    if "Telefon (Whatsapp):" in text:
        result_state = True
        
    if "Telefon (Whatsapp):" in text:
        result_state = True
        result_msg += "✅ FOUND: 'Telefon (Whatsapp)'\n"
    else:
        result_msg += "❌ NOT FOUND: 'Telefon (Whatsapp)'\n"

    if "Email: rustic_handmade@gmx.com" in text:
        result_msg += "✅ FOUND: 'Email: rustic_handmade@gmx.com'\n"
    else:
        result_state = False
        result_msg += "❌ NOT FOUND: 'Email: rustic_handmade@gmx.com'\n"

    print("=== CONTACT PAGE TEXT ===")
    print(text)
    print("=== END CONTACT PAGE TEXT ===")

finally:
    driver.quit()
    msg_manager.send(str(Path(__file__).stem), result_state, result_msg)        