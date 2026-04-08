from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.selenium_test_template import SeleniumTestTemplate, get_runtime
from pathlib import Path

class Test1(SeleniumTestTemplate):
    def __init__(self):
        super().__init__(str(Path(__file__).stem))

    def setup(self):
        pass

    @get_runtime
    def run_test_steps(self):
        self.driver.get("https://www.rustic-handmade.ro")
        wait = WebDriverWait(self.driver, 10)
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
            self.result_success = True

        if "Telefon (Whatsapp):" in text:
            self.result_success = True
            self.result_msg += "✅ FOUND: 'Telefon (Whatsapp)'\n"
        else:
            self.result_msg += "❌ NOT FOUND: 'Telefon (Whatsapp)'\n"

        if "Email: rustic_handmade@gmx.com" in text:
            self.result_msg += "✅ FOUND: 'Email: rustic_handmade@gmx.com'\n"
        else:
            self.result_success = False
            self.result_msg += "❌ NOT FOUND: 'Email: rustic_handmade@gmx.com'\n"

        self.log.info("=== CONTACT PAGE TEXT ===")
        self.log.info(text)
        self.log.info("=== END CONTACT PAGE TEXT ===")

    def teardown(self):
        pass


if __name__ == "__main__":
    Test1().execute()

