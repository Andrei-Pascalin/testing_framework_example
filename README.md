# 🧪 Testing Framework Example

An almost complete testing framework showcase featuring Selenium test automation with FastAPI and Flask servers for real-time result collection and visualization.

> **⚠️ Disclaimer:** This project is for skill expansion and learning purposes. It does not handle all edge cases. I would not use it in production environments without some serious testing...

---

## 📋 Overview

This project demonstrates:
- **Selenium test automation** with organized test discovery
- **FastAPI server** receiving test results in real-time
- **Flask dashboard** for visualizing test results
- **Graceful signal handling** (SIGINT/SIGTERM)
- **Centralized logging** to stdout and file
- **Process management** with automatic cleanup

---

## 🏗️ Architecture

```
test_runner.py
    ├─ FastAPI Server (Port 8100)
    │  └─ Receives test results
    ├─ Flask Dashboard (Port 8200)
    │  └─ Displays results & stats
    └─ Selenium Tests
       └─ Run and send results
```

---

## ✅ Completed Features

- [x] Selenium test automation
- [x] FastAPI server for result collection
- [x] Flask server with interactive dashboard
- [x] Test runner with server orchestration
- [x] Centralized logging system
- [x] Graceful signal handling and cleanup

---

## 📝 Planned Features

- [ ] Generic testing class with runtime measurement
- [ ] SQLAlchemy database integration for FastAPI
- [ ] Separate Flask templates and database queries
- [ ] Test result filtering and sorting
- [ ] Performance analytics and trends

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with servers
python test_runner.py

# Run with Flask server cleanup on exit
python test_runner.py --stop_results_page_srv

# Restart Flask server if already running
python test_runner.py --restart_results_page_srv
```
# Note
the Flask dashboard server will not be terminated by default upon test run end...
---

## 📊 View Results

Open your browser: `http://localhost:8200/dashboard`

---

## 📁 Project Structure

```
.
├── selenium_tests/          # Test files (test_*.py)
├── results_SRV/             # FastAPI server
├── show_results_srv/        # Flask dashboard
├── utils/                   # Logger & utilities
├── logs/                    # Log files (auto-created)
├── test_runner.py           # Main runner
├── requirements.txt
└── README.md

```

---

## 📜 License

See LICENSE file for details. 
