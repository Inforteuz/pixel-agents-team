import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_PUBLIC_URL"] = "http://127.0.0.1:8090"
os.environ["APP_ENV"] = "development"
