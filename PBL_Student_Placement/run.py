"""Start the placement portal:  python run.py  then open http://127.0.0.1:8091"""
import sys
from pathlib import Path

from app.server import main

if __name__ == "__main__":
    if "--db" not in sys.argv:
        sys.argv += ["--db", str(Path(__file__).resolve().parent / "data" / "usps.db")]
    main()
