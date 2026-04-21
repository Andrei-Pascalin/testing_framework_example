import sys
import re
import signal
import time
import subprocess
import argparse
import psutil
import requests

from pathlib import Path
from typing import List, Dict
from utils.my_logger import get_logger

log = get_logger()


# for not creating pyc files...
sys.dont_write_bytecode = True


TEST_PATTERN = re.compile(r"^test_(\d+)(.*?)\.py$")
TEST_DIR_NAME = "selenium_tests"
# asta e varianta mai traditionala de a afla CWD
# traditional ways of finding CWD
# CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))

CURRENT_PATH = Path(__file__).parent.resolve()

class Runner:
    def __init__(self, args):
        # if args.restart_results_page_srv:
        self.restart_results_page_srv = args.restart_results_page_srv
        self.stop_results_on_exit = args.stop_results_page_srv
        self.db_results_srv_process = None
        self.results_page_srv_process = None
        self.must_exit = False
        self.tests = []

    def __find_selenium_tests(self) -> List[Dict[str, str]]:
        """
        Recursively scans for files matching test_[digit].py pattern.
        Returns:
            List[Dict[str, str]]: list of test metadata
        """
        results: List[Dict[str, str]] = []

        base = CURRENT_PATH.joinpath(TEST_DIR_NAME)

        if not base.exists():
            return results

        for path in base.rglob("test_*.py"):
            if path.is_file():
                match = TEST_PATTERN.match(path.name)
                if match:
                    results.append({
                        "test_name": path.stem,
                        "test_path": str(path.parent.resolve())
                    })
        return results

    def __get_results_page_srv_process(self):
        for p in psutil.process_iter():
            try:
                # log.debug(f"Checking process: {p.name()} (PID: {p.pid}, Status: {p.status()}), Cmdline: {p.cmdline()}")
                contains = lambda lst: any("print_results_page_srv" in s for s in lst)
                if contains(p.cmdline()):
                    log.info("Found existing results page server process: %s (PID: %d, Status: %s)",
                             p.name(), p.pid, p.status())
                    return p
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    def __start_results_page_srv(self):
        existing_process = self.__get_results_page_srv_process()
        if existing_process:
            if not self.restart_results_page_srv:
                log.info(f"Existing Flask_results_web-page_server already running (PID: {existing_process.pid})"
                      "skipping start and no restart requested.")
                self.results_page_srv_process = existing_process
                return

            log.info("Restarting Flask_results_web-page_server as per CLI argument...")
            log.info(f"Terminating existing Flask_results_web-page_server (PID: {existing_process.pid})...")
            self.__terminate_process(existing_process)
        log.info("No existing Flask_results_web-page_server running so starting a new one.")
        # Start new server - run from project root so utils module is in path
        self.results_page_srv_process = subprocess.Popen([sys.executable, "-B", "-m",
                                                          "show_results_srv.print_results_page_srv"],
                                                          cwd=str(CURRENT_PATH),
                                                          stdout=subprocess.PIPE,
                                                          stderr=subprocess.PIPE,
                                                          start_new_session=True,
                                                          )
        # astea le folosim doar facem niscaiva debug la pornirea srv, pt ca ele sunt blocking de fapt
        # for line in self.results_page_srv_process.stdout:
        #     log.info(f"Flask Server: {line.decode().rstrip()}")
        # for line in self.results_page_srv_process.stderr:
        #     log.error(f"Flask Server Error: {line.decode().rstrip()}")
        log.info(f"Started Flask_results_web-page_server (PID: {self.results_page_srv_process.pid})")

    def __sigIntTerm_handler(self, signum, frame):
        log.info(f"Received signal {signum}, initiating cleanup...")
        self.must_exit = True
        # self.cleanup_servers()

    def __check_servers_alive(self, max_retries=5, retry_delay=0.3):
        """
        Check if both FastAPI and Flask servers are alive by pinging their /alive endpoints.
        Uses exponential backoff for retries.

        Args:
            max_retries: Number of retry attempts
            retry_delay: Initial delay between retries (increases exponentially)

        Raises:
            RuntimeError: If servers fail to respond within timeout
        """
        servers = [
            {"name": "FastAPI (DB Results)", "url": "http://localhost:8100/alive"},
            {"name": "Flask (Dashboard)", "url": "http://localhost:8200/alive"}
        ]

        failed_servers = {}

        for server in servers:
            log.info(f"Checking if {server['name']} is alive...")
            retry_count = 0
            delay = retry_delay
            is_alive = False

            while retry_count < max_retries and not is_alive:
                try:
                    response = requests.get(server["url"], timeout=2)
                    if response.status_code == 200:
                        log.info(f"✅ {server['name']} is alive")
                        is_alive = True
                        break
                except requests.exceptions.RequestException:
                    pass

                retry_count += 1
                if not is_alive:
                    if retry_count < max_retries:
                        log.debug(f"Retry {retry_count}/{max_retries} for {server['name']}...")
                        time.sleep(delay)
                        delay *= 1.1 # crestem timpul de asteptare
                    else:
                        failed_servers[server['name']] = f"No response after {max_retries} retries"
                        log.error(f"❌ {server['name']} is NOT responding")

            if not is_alive and server['name'] not in failed_servers:
                failed_servers[server['name']] = "Failed to start"

        if failed_servers:
            error_msg = "; ".join(failed_servers.values())
            raise RuntimeError(f"Servers health check failed: {error_msg}")

        log.info("🟢 All servers are alive and ready!")

    def start_servers(self):
        # acu pornim procesul serverului care primeste rezultatele testelor adica fastApi_SRV Selenium_results...
        # si optional le va salva intr-o baza de date si le vaforwarda catre un alt server care
        # le va afisa intr-o pagina web, adica flask_srv_process

        self.db_results_srv_process = subprocess.Popen([sys.executable, "-B", "-m", "uvicorn",
                                                        "results_SRV.fastApi_SRV_Selenium_results:app",
                                                        "--host", "localhost", "--port", "8100"],
                                                        cwd=str(CURRENT_PATH))

        time.sleep(1)
        log.info("Started FastAPI server (DB Results Receiver)")

        self.__start_results_page_srv()

        # Verify both servers are alive before proceeding
        self.__check_servers_alive()


    def run_tests(self):
        self.tests = self.__find_selenium_tests()
        log.debug(self.tests)
        if len(self.tests) == 0:
            log.error("Nu avem teste, hopaaaa, hai sa esim... :) ")
            raise Exception("Nu avem teste, hopaaaa, hai sa esim... :) ")

        # TODO need to find a better way to send the cwd to the subprocesses, maybe we can use env variables ...
        # What's a context manager ?? can it help in this case ?
        for test in self.tests:
            # should I check here if we should gracefully kill the test ?
            # in case sigterm happens ?
            if self.must_exit:
                log.info("Exiting test run loop due to signal interrupt.")
                raise KeyboardInterrupt()
            test_proc = subprocess.Popen([sys.executable, "-B",
                                          "-m",
                                          "selenium_tests." + test.get(r"test_name")],
                                          cwd=CURRENT_PATH)
            test_proc.wait()

    # this is how we elegantly terminate a process (at least linux style)
    def __terminate_process(self, process: psutil.Process, timeout=5):
        # TODO check for zombie ???
        try:
            proc_str_msg = f"{process.name()} - {process.cmdline()} (PID: {process.pid})"
        except psutil.ZombieProcess:
            log.error(f"Process {process.pid} is a zombie, cannot terminate.")
            return
        log.info(f"Terminating existing {proc_str_msg}...")
        try:
            process.terminate()
            process.wait(timeout=timeout)
            log.info(f"Existing {proc_str_msg} terminated.")
        except subprocess.TimeoutExpired:
            log.error("Graceful terminate timed out; killing process...")
            try:
                # kill raises NoSUchProcess
                process.kill()
                process.wait(timeout=timeout)
            except psutil.NoSuchProcess:
                 log.error(f"Process {process.pid} already terminated.")
            except subprocess.TimeoutExpired:
                log.error(f"Failed to kill process {process.pid} within timeout.")
            except Exception as e:
                log.error(f"Failed to kill existing process: {e}")
        except Exception as e:
            log.error(f"Error while stopping existing process: {e}")

    def cleanup_servers(self):
        # TODO add better logic, handle timeout and force terminate cases,
        # also handle the case when the server is already stopped by the user or by an error in
        # the server code, we should not try to terminate it again in that case.
        if self.db_results_srv_process:
            self.__terminate_process(psutil.Process(self.db_results_srv_process.pid))

        if self.results_page_srv_process and self.stop_results_on_exit:
            self.__terminate_process(psutil.Process(self.results_page_srv_process.pid))

    def run(self):
        signal.signal(signal.SIGINT, self.__sigIntTerm_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, self.__sigIntTerm_handler)  # Kill signal

        try:
            self.start_servers()
            self.run_tests()
        except KeyboardInterrupt:
            log.error("Test run interrupted by user.")
            # sigint exit code
            return 130
        except Exception as e:
            log.error(f"Error during test execution: {e}")
            return 1
        finally:
            self.cleanup_servers()

        return 0




def main():
    parser = argparse.ArgumentParser(description="Run selenium tests with optional servers")

    parser.add_argument("--restart_results_page_srv", action="store_true", default=False,
                        help="Restart the results (Flask) server if it's already running")

    parser.add_argument("--stop_results_page_srv", action="store_true", default=False,
                        help="Stop the results (Flask) server at the end of the test run")

    args, _ = parser.parse_known_args()

    my_tests_runner = Runner(args)
    return my_tests_runner.run()

if __name__ == "__main__":
    # signal.signal(signal.SIGINT, cleanup)    # CTRL+C
    # signal.signal(signal.SIGTERM, cleanup)   # KILL signal
    sys.exit(main())
