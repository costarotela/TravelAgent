"""Main entry point for the Travel Agent application."""
import os
from pathlib import Path

import streamlit.web.bootstrap as bootstrap
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up paths
ROOT_DIR = Path(__file__).parent
os.environ["PYTHONPATH"] = str(ROOT_DIR)

# Run the Streamlit application
if __name__ == "__main__":
    bootstrap.run(
        str(ROOT_DIR / "src" / "ui" / "main.py"),
        "",
        [],
        flag_options={}
    )
