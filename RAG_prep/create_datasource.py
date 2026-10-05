"""
Creates (or updates) the Azure AI Search *data source* that points at the Cosmos DB container.
setup_search.py expects a data source with this exact name, so creating it here means you don't
have to click through the portal.

Reads the same .env as the other RAG_prep scripts:
SERVICE_NAME, ADMIN_KEY, COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE_NAME, COSMOS_CONTAINER_NAME
"""
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
    HighWaterMarkChangeDetectionPolicy,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
)

load_dotenv()

DATA_SOURCE_NAME = "cba-support-docs"  # must match data_source_name in setup_search.py

search_endpoint = f"https://{os.environ['SERVICE_NAME']}.search.windows.net/"

# Search expects: AccountEndpoint=https://<account>.documents.azure.com;AccountKey=<key>;Database=<db>
cosmos_host = urlparse(os.environ["COSMOS_ENDPOINT"]).hostname
connection_string = (
    f"AccountEndpoint=https://{cosmos_host};"
    f"AccountKey={os.environ['COSMOS_KEY']};"
    f"Database={os.environ['COSMOS_DATABASE_NAME']}"
)

data_source = SearchIndexerDataSourceConnection(
    name=DATA_SOURCE_NAME,
    type="cosmosdb",
    connection_string=connection_string,
    container=SearchIndexerDataContainer(name=os.environ["COSMOS_CONTAINER_NAME"]),
    # Lets the indexer pick up only new/changed documents on later runs.
    data_change_detection_policy=HighWaterMarkChangeDetectionPolicy(high_water_mark_column_name="_ts"),
)

client = SearchIndexerClient(search_endpoint, AzureKeyCredential(os.environ["ADMIN_KEY"]))
client.create_or_update_data_source_connection(data_source)
print(f"Data source '{DATA_SOURCE_NAME}' created or updated.")
