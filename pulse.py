"""
ReviewPulse AI command line.

    python pulse.py demo         Mock reviews, local clustering, no API keys
    python pulse.py fetch        Pull recent reviews from Google Play
    python pulse.py process      Cluster untriaged reviews with Gemini
    python pulse.py ui [--demo]  Open the Streamlit dashboard

The demo uses its own database (data/demo.db), so it never mixes with real reviews.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO_DB_PATH = os.path.join(ROOT, "data", "demo.db")
DEMO_DB_URL = f"sqlite:///{DEMO_DB_PATH}"
DEMO_REPORT_PATH = os.path.join(ROOT, "data", "demo_output.md")


def use_demo_database():
    # Settings are read when core.config is first imported, so this must run before any core import.
    os.environ["DATABASE_URL"] = DEMO_DB_URL


def create_schema():
    from core.database import Base, engine
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    Base.metadata.create_all(bind=engine)


def run_demo():
    use_demo_database()
    # Remove the WAL sidecars too: SQLite can replay a stale -wal file into a fresh database.
    for path in (DEMO_DB_PATH, f"{DEMO_DB_PATH}-wal", f"{DEMO_DB_PATH}-shm"):
        if os.path.exists(path):
            os.remove(path)
    create_schema()

    from core.analyzer import ReviewAnalyzer
    from core.database import SessionLocal
    from core.demo import KeywordClusterer, print_summary, seed_mock_reviews, write_report

    db = SessionLocal()
    try:
        print(f"Seeded {seed_mock_reviews(db)} mock reviews into data/demo.db")
    finally:
        db.close()

    stats = ReviewAnalyzer(clusterer=KeywordClusterer()).run_analysis()
    if not stats:
        print("Demo failed: no clusters were produced.")
        return 1

    print()
    print_summary(stats)
    write_report(stats, DEMO_REPORT_PATH)
    print()
    print("Report: data/demo_output.md")
    print("Dashboard: python pulse.py ui --demo")
    return 0


def run_fetch():
    create_schema()
    from scripts.fetch_reviews import main
    main()
    return 0


def run_process():
    from scripts.process_reviews import main
    main()
    return 0


def run_ui(demo: bool):
    env = dict(os.environ, PYTHONPATH=ROOT)
    if demo:
        if not os.path.exists(DEMO_DB_PATH):
            print("No demo data yet. Run: python pulse.py demo")
            return 1
        env.update(DATABASE_URL=DEMO_DB_URL, REVIEWPULSE_DEMO="1")
    cmd = [sys.executable, "-m", "streamlit", "run", os.path.join(ROOT, "app", "main.py")]
    return subprocess.call(cmd, cwd=ROOT, env=env)


def main():
    parser = argparse.ArgumentParser(prog="pulse.py", description="ReviewPulse AI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="run the pipeline on mock reviews, no API keys needed")
    sub.add_parser("fetch", help="pull recent reviews from Google Play")
    sub.add_parser("process", help="cluster untriaged reviews with Gemini")
    ui = sub.add_parser("ui", help="open the Streamlit dashboard")
    ui.add_argument("--demo", action="store_true", help="show the demo database")
    args = parser.parse_args()

    if args.command == "demo":
        return run_demo()
    if args.command == "fetch":
        return run_fetch()
    if args.command == "process":
        return run_process()
    return run_ui(args.demo)


if __name__ == "__main__":
    sys.exit(main())
