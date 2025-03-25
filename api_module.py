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

def make_api_request(api_key: str, message_history: list, model: str, temperature: float = 1.0, stream: bool = False, context_length: int | None = None, max_completion_tokens: int | None = None, reasoning_effort: str | None = None, reasoning_max_tokens: int | None = None, exclude_reasoning: bool = False):
    """
    Make a POST request to the OpenRouter API for a specific model.

    Args:
        api_key (str): The API key for authorization.
        message_history (list): The conversation history.
        model (str): The AI model to use for generating a response.
        temperature (float, optional): Sampling temperature. Defaults to 1.0.
        stream (bool, optional): Whether to stream the response in chunks.
        context_length (int, optional): The maximum number of tokens for context. Defaults to None.
        max_completion_tokens (int, optional): The maximum number of tokens for the completion. Defaults to None.
        reasoning_effort (str, optional): The reasoning effort level ("high", "medium", "low"). Defaults to None.
        reasoning_max_tokens (int, optional): The maximum tokens for reasoning. Defaults to None.
        exclude_reasoning (bool, optional): Whether to exclude reasoning tokens from response. Defaults to False.

    Yields:
        str: The content chunk from the AI response.

    Returns:
        dict: The JSON response from the API if stream is False.

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
        "messages": message_history,
        "temperature": temperature,
        "stream": stream
    }

    # Add context_length and max_completion_tokens to payload if provided
    if context_length is not None:
        payload["max_tokens"] = context_length
    if max_completion_tokens is not None:
        payload["max_completion_tokens"] = max_completion_tokens
    
    # Add reasoning parameters if needed
    if reasoning_effort is not None or reasoning_max_tokens is not None or exclude_reasoning:
        payload["reasoning"] = {}
        if reasoning_effort:
            payload["reasoning"]["effort"] = reasoning_effort
        if reasoning_max_tokens:
            payload["reasoning"]["max_tokens"] = reasoning_max_tokens
        if exclude_reasoning:
            payload["reasoning"]["exclude"] = True

    try:
        with requests.post(url, headers=headers, json=payload, stream=stream) as response:
            response.raise_for_status()  # Raises HTTPError for bad responses

            if stream:
                # Stream the response chunk by chunk
                for chunk in response.iter_lines():
                    if chunk:
                        decoded_chunk = chunk.decode("utf-8")
                        if decoded_chunk.strip() == "[DONE]":
                            break
                        else:
                            # Remove 'data: ' prefix if present
                            if decoded_chunk.startswith('data: '):
                                decoded_chunk = decoded_chunk[len('data: '):]

                            try:
                                chunk_data = json.loads(decoded_chunk)
                                # Extract the content from the chunk
                                if "choices" in chunk_data:
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        text = delta["content"]
                                        yield text
                            except json.JSONDecodeError:
                                continue
            else:
                # Non-streaming: return the full JSON response
                return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed for model '{model}': {e}")
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON response.")