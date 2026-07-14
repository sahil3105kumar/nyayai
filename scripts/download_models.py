"""
first time setup script. downloads:
  1. legal corpus PDFs from IndiaCode (official govt source)
  2. spacy NER model
  3. optionally pulls InLegalBERT tokenizer cache

run once before ingesting corpus:
  uv run python scripts/download_models.py
"""

import os
import sys
import urllib.request

from config.settings import settings

SOURCES_DIR = settings.corpus_sources_dir

# direct PDF URLs from indiacode.nic.in - official government source
# all confirmed working as of July 2025
ACTS = [
    {
        "name": "IPC",
        "filename": "ipc.pdf",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/15289/1/ipc_act.pdf",
        "dir": "ipc",
        "status": "repealed",  # replaced by BNS from July 1 2024
    },
    {
        "name": "BNS",
        "filename": "bns.pdf",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf",
        "dir": "bns",
        "status": "active",
    },
    {
        "name": "BNSS",
        "filename": "bnss.pdf",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/20340/1/bnss,_2023.pdf",
        "dir": "bnss",
        "status": "active",
    },
    {
        "name": "Constitution",
        "filename": "constitution.pdf",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/19151/1/constitution_of_india.pdf",
        "dir": "constitution",
        "status": "active",
    },
    {
        "name": "CPC",
        "filename": "cpc.pdf",
        "url": "https://www.indiacode.nic.in/indiacode/bitstream/123456789/2191/1/aA1908-05.pdf",
        "dir": "cpc",
        "status": "active",
    },
]


def download_file(url: str, dest: str, name: str):
    if os.path.exists(dest):
        size = os.path.getsize(dest)
        print(f"  {name}: already exists ({size // 1024}KB), skipping")
        return True

    print(f"  {name}: downloading from IndiaCode...")
    try:
        req = urllib.request.Request(
            url,
            headers={
                # IndiaCode requires a browser-like user agent
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read()

        with open(dest, "wb") as f:
            f.write(data)

        size = len(data)
        print(f"  {name}: downloaded ({size // 1024}KB)")
        return True

    except Exception as e:
        print(f"  {name}: FAILED — {e}")
        print(f"  manual download: {url}")
        return False


def download_acts():
    print("\n--- downloading legal corpus PDFs ---")
    failed = []

    for act in ACTS:
        act_dir = os.path.join(SOURCES_DIR, act["dir"])
        os.makedirs(act_dir, exist_ok=True)
        dest = os.path.join(act_dir, act["filename"])
        ok = download_file(act["url"], dest, act["name"])
        if not ok:
            failed.append(act["name"])

    if failed:
        print(f"\nfailed to download: {', '.join(failed)}")
        print("download them manually from https://www.indiacode.nic.in and place in corpus/sources/")
    else:
        print("\nall acts downloaded successfully")

    return len(failed) == 0


def download_spacy_model():
    print("\n--- downloading spacy NER model ---")
    try:
        import spacy
        try:
            spacy.load("en_core_web_sm")
            print("  en_core_web_sm: already installed")
        except OSError:
            print("  en_core_web_sm: downloading...")
            os.system(f"{sys.executable} -m spacy download en_core_web_sm")
            print("  en_core_web_sm: done")
    except ImportError:
        print("  spacy not installed — run: uv add spacy")


def verify():
    print("\n--- verifying downloads ---")
    all_ok = True
    for act in ACTS:
        path = os.path.join(SOURCES_DIR, act["dir"], act["filename"])
        exists = os.path.exists(path)
        size = os.path.getsize(path) // 1024 if exists else 0
        status = f"OK ({size}KB)" if exists else "MISSING"
        print(f"  {act['name']}: {status}")
        if not exists:
            all_ok = False
    return all_ok


if __name__ == "__main__":
    print("NyayAI first-time setup")
    print("=" * 40)

    acts_ok = download_acts()
    download_spacy_model()
    verify()

    print("\n" + "=" * 40)
    if acts_ok:
        print("setup complete. next step:")
        print("  uv run python scripts/ingest_corpus.py --all")
    else:
        print("some downloads failed. fix them before running ingest.")