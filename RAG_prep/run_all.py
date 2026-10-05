"""
Builds the whole knowledge base in one go:
  1. scrape the CommBank support pages      -> RAG_prep/all_documents.json
  2. upload them to Cosmos DB
  3. create the AI Search data source
  4. create the search index + indexer, then wait for the indexer to finish

Usage (from anywhere, with your .env in the project root):
    python RAG_prep/run_all.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexerClient

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

STEPS = [
    ("Scraping CommBank support pages", "RAG_prep/scrape_data.py"),
    ("Uploading documents to Cosmos DB", "RAG_prep/upload_docs.py"),
    ("Creating the AI Search data source", "RAG_prep/create_datasource.py"),
    ("Creating the search index and indexer", "RAG_prep/setup_search.py"),
]


def run(title: str, script: str) -> None:
    print(f"\n=== {title} ===", flush=True)
    if subprocess.run([sys.executable, script], cwd=ROOT).returncode != 0:
        sys.exit(f"\nStep failed: {title}. Fix the error shown above, then run this again.")


def check_scrape() -> None:
    docs_file = ROOT / "RAG_prep" / "all_documents.json"
    count = len(json.loads(docs_file.read_text(encoding="utf-8"))) if docs_file.exists() else 0
    print(f"Scraped {count} pages.")
    if count == 0:
        sys.exit("No pages were scraped (is Microsoft Edge installed? did the site change?). Stopping here.")


def wait_for_indexer(timeout_s: int = 240) -> None:
    endpoint = f"https://{os.environ['SERVICE_NAME']}.search.windows.net/"
    credential = AzureKeyCredential(os.environ["ADMIN_KEY"])
    indexer_client = SearchIndexerClient(endpoint, credential)
    print("\n=== Waiting for the indexer ===", flush=True)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        last = indexer_client.get_indexer_status("cosmosdb-indexer").last_result
        status = str(last.status) if last else "not started yet"
        print(f"  indexer status: {status}", flush=True)
        if last and "inProgress" not in status and "not started" not in status:
            break
        time.sleep(10)
    if last and "success" in str(last.status).lower():
        print(f"Indexer finished: {last.item_count} documents processed, {last.failed_item_count} failed.")
    else:
        msg = last.error_message if last else "timed out"
        print(f"Indexer did not report success: {msg}\nCheck Search service > Indexers in the portal for details.")
    client = SearchClient(endpoint, os.environ["INDEX_NAME"], credential)
    print(f"Documents now in the index: {client.get_document_count()}")


if __name__ == "__main__":
    for i, (title, script) in enumerate(STEPS):
        run(title, script)
        if i == 0:
            check_scrape()
    wait_for_indexer()
    print("\nDone. The knowledge base is ready.")
