import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from .utils import get_secret


# Azure OpenAI configuration (set in local.settings.json locally, or Function App configuration in Azure).
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]                 # e.g. https://<resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-06-01")
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]             # name of your chat model deployment
# Optional: a smaller/cheaper deployment for the search-query rewrite step. Falls back to the main deployment.
AZURE_OPENAI_QUERY_DEPLOYMENT = os.environ.get("AZURE_OPENAI_QUERY_DEPLOYMENT", AZURE_OPENAI_DEPLOYMENT)


def _build_client() -> AzureOpenAI:
    """
    Creates the Azure OpenAI client.

    Authentication:
      - USE_ENTRA_AUTH=true  -> keyless, using the Function App's managed identity via Microsoft Entra ID
                                (the identity needs the "Cognitive Services OpenAI User" role on the resource).
      - otherwise            -> API key retrieved from Azure Key Vault (secret name: 'azure-openai-api-key').
    """
    if os.environ.get("USE_ENTRA_AUTH", "false").lower() == "true":
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        return AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=AZURE_OPENAI_API_VERSION,
        )

    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=get_secret("azure-openai-api-key"),
        api_version=AZURE_OPENAI_API_VERSION,
    )


# Created once per Function App instance and reused across invocations.
client = _build_client()


def generate_openai_response(prompt_text: str, system_message: str, deployment: str = None) -> str:
    """
    Generates a chat completion from an Azure OpenAI Service deployment.

    Args:
        prompt_text (str): The user's input text to which the model should respond.
        system_message (str): A system-level message that provides context for the conversation.
                              This is used to prime the model for generating responses in a specific context.
        deployment (str): The Azure OpenAI deployment name (not the base model name).
                          Defaults to AZURE_OPENAI_DEPLOYMENT.

    Returns:
        str or None: The generated response from the model, or None if an error occurs during the API call.

    Raises:
        Prints an error message to the console if the Azure OpenAI call fails.
    """

    try:
        response = client.chat.completions.create(
            model=deployment or AZURE_OPENAI_DEPLOYMENT,  # In Azure OpenAI, 'model' is the deployment name.
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.7,
            max_tokens=256,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling Azure OpenAI: {e}")
        return None
