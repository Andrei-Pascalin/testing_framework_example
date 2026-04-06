import sys
import re
import signal
from pathlib import Path
import time
from typing import List, Dict
from multiprocessing import Process
import subprocess

TEST_PATTERN = re.compile(r"^test_(\d+)(.*?)\.py$")
TEST_DIR_NAME = "selinium tests"
# asta e varianta mai traditionala de a afla CWD
# traditional ways of finding CWD
# CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))

CURRENT_PATH = Path(__file__).parent
CURRENT_PATH = Path(__file__).parent

last_running_process = None
last_lev_process = None

def find_selenium_tests() -> List[Dict[str, str]]:
    """
    Recursively scans for files matching test_... pattern.
    Returns:
        List[Dict[str, str]]: list of test metadata
    """
    results: List[Dict[str, str]] = []

    base = CURRENT_PATH.joinpath("tests", "src", "xxv")
    if not base.exists():
        return results

    for path in base.rglob("test_*.py"):
        name = path.name
        m = TEST_PATTERN.match(name)
        if not m:
            continue
        # ... rest of parsing and metadata collection ...
        results.append({
            "path": str(path),
            "name": name,
            "match": m.group(0)
        })

    return results

def cleanup(signum, frame):
    print("Script received termination signal. Cleaning up...")
    global results_srv_process, flask_srv_process
    if results_srv_process:
        results_srv_process.terminate()
    if flask_srv_process:
        flask_srv_process.terminate()
    sys.exit(1)

def main() -> int:
    global results_srv_process, flask_srv_process
    tests = []
    tests = find_selenium_tests()
    print(tests)
    if len(tests) == 0:
        print("Nu avem teste, hopaaaa, hai sa esim... :) ")
        return 1
    # acu pornim procesul serverului care primeste rezultatele testelor...
    # adica fastApi_SRV Selenium_results
    
 
    results_srv_process = subprocess.Popen([sys.executable,
                                            "fastApi_SRV_selenium_results.app",
                                            "--host", "127.0.0.1", "--port", "8100"],
                                            cwd="results_srv")

    time.sleep(3)
    print("am pornit procesul srv-ului de asteptare a datelor de la teste ...")
    # Start Flask server on port 8280
    flask_srv_process = subprocess.Popen([sys.executable,
        "print_results_page_srv.py"],
        cwd="show_results_srv")

    time.sleep(3)
    print("am pornit Flask server-ul pe localhost:8280 ...")

    for test in tests:
        test_proc = subprocess.Popen([sys.executable,
            "-m",
            "selenium_tests." + test.get("test_name")],
            cwd=Path("c:\Testing framework example")
        )
        test_proc.wait()

    results_srv_process.terminate()
    flask_srv_process.terminate()
    return 0

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)    # CTRL+C
    signal.signal(signal.SIGTERM, cleanup)   # KILL signal
    sys.exit(main())   
    