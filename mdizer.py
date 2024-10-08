# mdizer.py

import markdown2

def markdown_to_html(md_text: str) -> str:
    """
    Convert markdown text to HTML.

    Args:
        md_text (str): The markdown text to convert.

    Returns:
        str: The converted HTML text.
    """
    return markdown2.markdown(md_text)
