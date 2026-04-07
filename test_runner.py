import sys
import re
import signal
import time
import subprocess
import argparse
import psutil

from pathlib import Path
from typing import List, Dict

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
                if "print_results_page_srv.py" in p.cmdline():
                    print(p.name(), p.pid, p.status(), p.cmdline())
                    return p
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None
        
    def __start_results_page_srv(self):
        existing_process = self.__get_results_page_srv_process()
        if existing_process:
            if not self.restart_results_page_srv:
                print(f"Existing results page server already running (PID: {existing_process.pid})"
                      "skipping start and no restart requested.")
                self.results_page_srv_process = existing_process
                return

            print("Restarting results page server as per CLI argument...")
            print(f"Terminating existing results page server (PID: {existing_process.pid})...")
            self.__terminate_process(existing_process)
        print("No existing results page running so starting a new one.")
        # Start new server
        self.results_page_srv_process = subprocess.Popen([sys.executable, "print_results_page_srv.py"],
                                                        cwd="show_results_srv",
                                                        stdout=subprocess.PIPE,
                                                        stderr=subprocess.PIPE,
                                                        start_new_session=True)
        print(f"Started (Flask) results page server (PID: {self.results_page_srv_process.pid})")

    def __sigIntTerm_handler(self, signum, frame):
        print(f"Received signal {signum}, initiating cleanup...")
        self.must_exit = True 
        # self.cleanup_servers()
        

    def start_servers(self):
        # acu pornim procesul serverului care primeste rezultatele testelor adica fastApi_SRV Selenium_results...
        # si optional le va salva intr-o baza de date si le vaforwarda catre un alt server care 
        # le va afisa intr-o pagina web, adica flask_srv_process
        
        self.db_results_srv_process = subprocess.Popen([sys.executable, "-m", "uvicorn",
                                                        "fastApi_SRV_Selenium_results:app",
                                                        "--host", "127.0.0.1", "--port", "8100"],
                                                        cwd="results_SRV")

        time.sleep(3)
        print("am pornit procesul srv-ului de asteptare a datelor de la teste ...")

        self.__start_results_page_srv()

        
    def run_tests(self):
        self.tests = self.__find_selenium_tests()
        print(self.tests)
        if len(self.tests) == 0:
            print("Nu avem teste, hopaaaa, hai sa esim... :) ")
            raise Exception("Nu avem teste, hopaaaa, hai sa esim... :) ")

        # TODO need to find a better way to send the cwd to the subprocesses, maybe we can use env variables ...
        # What's a context manager ?? can it help in this case ?
        for test in self.tests:
            # should I check here if we should gracefully kill the test ?
            # in case sigterm happens ?
            if self.must_exit:
                print("Exiting test run loop due to signal interrupt.")
                raise KeyboardInterrupt()
            test_proc = subprocess.Popen([sys.executable,
                                          "-m",
                                          "selenium_tests." + test.get(r"test_name")],
                                          cwd=CURRENT_PATH)
            test_proc.wait()
    
    # this is how we elegantly terminate a process (at least linux style)
    def __terminate_process(self, process: psutil.Process, timeout=5):
        proc_str_msg = f"{process.name()} - {process.cmdline()} (PID: {process.pid})"
        print(f"Terminating existing {proc_str_msg}...")
        try:
            process.terminate()
            process.wait(timeout=timeout)
            print(f"Existing {proc_str_msg} terminated.")
        except subprocess.TimeoutExpired:
            print("Graceful terminate timed out; killing process...")
            try:
                # kill raises NoSUchProcess
                process.kill()
                process.wait(timeout=timeout)
            except psutil.NoSuchProcess:
                 print(f"Process {process.pid} already terminated.")
            except subprocess.TimeoutExpired:
                print(f"Failed to kill process {process.pid} within timeout.")
            except Exception as e:
                print(f"Failed to kill existing process: {e}")
        except Exception as e:
            print(f"Error while stopping existing process: {e}")
        
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
            print("Test run interrupted by user.")
            # sigint exit code
            return 130
        except Exception as e:
            print(f"Error during test execution: {e}" )
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

    args, unknown = parser.parse_known_args()

    my_tests_runner = Runner(args)
    return my_tests_runner.run()

if __name__ == "__main__":
    # signal.signal(signal.SIGINT, cleanup)    # CTRL+C
    # signal.signal(signal.SIGTERM, cleanup)   # KILL signal
    sys.exit(main())   
    