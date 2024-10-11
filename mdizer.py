import markdown

def markdown_to_html(markdown_text):
    html = markdown.markdown(markdown_text, extensions=['fenced_code', 'tables'])
    # Add CSS styling for better readability
    style = """
    <style>
        pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
        }
        code {
            font-family: Consolas, monospace;
            font-size: 13px;
        }
        table {
            border-collapse: collapse;
        }
        table, th, td {
            border: 1px solid black;
        }
        th, td {
            padding: 5px;
            text-align: left;
        }
    </style>
    """
    return style + html
