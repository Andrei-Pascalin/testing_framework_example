import time

from abc import ABC, abstractmethod
from selenium import webdriver

from utils.my_logger import get_logger
from utils.test_results_sender import SendingManager

from functools import wraps

def get_runtime(func):
    @wraps(func)
    def get_runtime_wrapper(*args, **kwargs):
        start_time = time.time()
        # we don't need any result from the called function
        # we only want the runtime
        func(*args, **kwargs)
        end_time = time.time()
        total_time = end_time - start_time
        print(f'Function {func.__name__} took {total_time:.4f} seconds')
        return time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime(start_time)), round(total_time, 2)
    return get_runtime_wrapper

class SeleniumTestTemplate(ABC):
    def __init__(self, test_name, browser=webdriver.Chrome):
        self.test_name = test_name
        self.log = get_logger(log_filename=self.test_name + ".log")
        self.driver = None
        self.msg_manager = SendingManager()
        self.browser = browser
        self.result_success = False
        self.result_msg = ""
        self.runtime = 0.0
        self.start_time = 0.0

    def __setup(self):
        if self.browser is webdriver.Chrome:
            self.driver = webdriver.Chrome()
        elif self.browser is webdriver.Firefox:
            options = webdriver.FirefoxOptions()
            self.driver = webdriver.Firefox(options=options)
        elif self.browser is webdriver.ChromiumEdge:
            self.driver = webdriver.ChromiumEdge()
        else:
            raise ValueError("Unsupported browser type")
        # in this way we can have some common setup logic here,
        # and the specific test can have its own setup logic in the overridden
        self.setup

    @abstractmethod
    def setup(self):
        pass

    @get_runtime
    @abstractmethod
    def run_test_steps(self):
        pass

    @abstractmethod
    def teardown(self):
        pass

    def __teardown(self):
        if self.driver:
            self.driver.quit()
        # in this way we can have some common teardown logic here,
        # and the specific test can have its own teardown logic in the overridden method if needed
        self.teardown()

    def execute(self):
        self.__setup()
        try:
            self.start_time, self.runtime = self.run_test_steps()
        finally:
            self.__teardown()
            self.msg_manager.send(self.test_name, self.result_success, self.result_msg,
                                  self.start_time, self.runtime)