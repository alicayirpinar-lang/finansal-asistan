"""Tez takibi girişi: python track.py — açık tezleri kontrol eder."""
from dotenv import load_dotenv

load_dotenv()

from src import tracker

if __name__ == "__main__":
    tracker.run()
