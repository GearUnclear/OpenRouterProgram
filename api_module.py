# api_module.py

import requests
import json
import win32cred

def get_api_key(credential_name: str) -> str:
    """
    Retrieve the API key from Windows Credential Manager.

    Args:
        credential_name (str): The name of the credential to retrieve.

    Returns:
        str: The decoded API key.

    Raises:
        Exception: If the credential cannot be read or decoded.
    """
    try:
        credential = win32cred.CredRead(
            TargetName=credential_name,
            Type=win32cred.CRED_TYPE_GENERIC
        )
        api_key = credential['CredentialBlob'].decode('utf-16')
        return api_key
    except Exception as e:
        raise Exception(f"Error retrieving API key: {e}")

def make_api_request(api_key: str, message_history: list, model: str) -> dict:
    """
    Make a POST request to the OpenRouter API for a specific model.

    Args:
        api_key (str): The API key for authorization.
        message_history (list): The conversation history.
        model (str): The AI model to use for generating a response.

    Returns:
        dict: The JSON response from the API.

    Raises:
        Exception: If the request fails or the response is invalid.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": message_history
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raises HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed for model '{model}': {e}")
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON response.")

def format_response(response_json: dict, model: str) -> str:
    """
    Formats the JSON response into a clean, readable string.

    Args:
        response_json (dict): The JSON response from the API.
        model (str): The model that was used for the request.

    Returns:
        str: The formatted response.
    """
    formatted_output = f"### Model: {model}\n"
    if "choices" in response_json and len(response_json["choices"]) > 0:
        for i, choice in enumerate(response_json["choices"], start=1):
            content = choice.get('message', {}).get('content', '').strip()
            if content:
                formatted_output += f"**Choice {i}:**\n{content}\n\n"
    elif "error" in response_json:
        formatted_output += f"**Error:** {response_json['error']}\n"
    else:
        formatted_output += "Unexpected response format.\n"
    
    formatted_output += "-" * 50 + "\n"
    return formatted_output
