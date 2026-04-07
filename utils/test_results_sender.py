import requests
from utils.my_logger import get_logger

log = get_logger()

SERVER_URL = "http://127.0.0.1:8100/result"

class Result:
    def __init__(self, test_name, success, text):
        self._test_name = test_name
        self._success = success
        self._text = text

    def get_success(self):
        return self._success

    def get_text(self):
        return self._text

    def get_test_name(self):
        return self._test_name

class TestResultSender:
    def __init__(self, url):
        self.url = url

    def send_result(self, test_name, success, text):
        data = {
            "test_name": test_name,
            "success": success,
            "text": text
        }

        # log.info("Sending data to server:", data)
        response = requests.post(self.url, json=data)
        return response.json()

class SendingManager:
    def __init__(self):
        self.sender = TestResultSender(SERVER_URL)

    def send(self, test_name, success, text):
        result = Result(test_name, success, text)
        return self.sender.send_result(result.get_test_name(),
                                       result.get_success(),
                                       result.get_text())
        
        
        
        