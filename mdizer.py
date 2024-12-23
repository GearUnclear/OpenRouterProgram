import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from pymdownx.highlight import HighlightExtension

def markdown_to_html(markdown_text):
    """
    Converts markdown text to HTML with enhanced formatting and syntax highlighting.

    Args:
        markdown_text (str): The markdown content to convert.

    Returns:
        str: The resulting HTML content with embedded CSS styling.
    """
    # Define markdown extensions with pymdownx enhancements
    extensions = [
        'tables',
        FencedCodeExtension(),
        CodeHiliteExtension(css_class='highlight', linenums=False),
        HighlightExtension(),
        'pymdownx.superfences',  # Use as a string, not an import
        'pymdownx.extra',  # Includes a collection of useful extensions
    ]

    # Create markdown processor with specified extensions
    md = markdown.Markdown(extensions=extensions, extension_configs={
        'codehilite': {
            'css_class': 'highlight',
            'linenums': False,
            'guess_lang': False
        },
        'pymdownx.superfences': {
            'custom_fences': [
                {
                    'name': 'html',
                    'class': 'html-code',
                    'format': 'html',
                },
                # Add more custom fences if needed
            ]
        }
    })

    # Convert markdown to HTML
    html = md.convert(markdown_text)

    # Enhanced CSS styling for better readability and syntax highlighting
    style = """
    <style>
        /* Base styling for code blocks */
        pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: Consolas, monospace;
            font-size: 13px;
        }
        code {
            font-family: Consolas, monospace;
            font-size: 13px;
        }
        .highlight {
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        /* Styling for tables */
        table {
            border-collapse: collapse;
            margin-bottom: 10px;
            width: 100%;
        }
        table, th, td {
            border: 1px solid #ddd;
        }
        th, td {
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        /* Syntax highlighting styles */
        /* You can customize these styles or use a CSS framework like highlight.js or Prism */
        .highlight .hll { background-color: #ffffcc }
        .highlight  { background: #f0f0f0; }
        .highlight .c { color: #408080; font-style: italic } /* Comment */
        .highlight .err { border: 1px solid #FF0000 } /* Error */
        .highlight .k { color: #008000; font-weight: bold } /* Keyword */
        .highlight .o { color: #666666 } /* Operator */
        .highlight .cm { color: #408080; font-style: italic } /* Comment.Multiline */
        .highlight .cp { color: #BC7A00 } /* Comment.Preproc */
        .highlight .c1 { color: #408080; font-style: italic } /* Comment.Single */
        .highlight .cs { color: #408080; font-style: italic } /* Comment.Special */
        .highlight .gd { color: #A00000 } /* Generic.Deleted */
        .highlight .ge { font-style: italic } /* Generic.Emph */
        .highlight .gr { color: #FF0000 } /* Generic.Error */
        .highlight .gh { color: #000080; font-weight: bold } /* Generic.Heading */
        .highlight .gi { color: #00A000 } /* Generic.Inserted */
        .highlight .go { color: #808080 } /* Generic.Output */
        .highlight .gp { color: #000080; font-weight: bold } /* Generic.Prompt */
        .highlight .gs { font-weight: bold } /* Generic.Strong */
        .highlight .gu { color: #800080; font-weight: bold } /* Generic.Subheading */
        .highlight .gt { color: #0044DD } /* Generic.Traceback */
        .highlight .kc { color: #008000; font-weight: bold } /* Keyword.Constant */
        .highlight .kd { color: #008000; font-weight: bold } /* Keyword.Declaration */
        .highlight .kn { color: #008000; font-weight: bold } /* Keyword.Namespace */
        .highlight .kp { color: #008000 } /* Keyword.Pseudo */
        .highlight .kr { color: #008000; font-weight: bold } /* Keyword.Reserved */
        .highlight .kt { color: #B00040 } /* Keyword.Type */
        .highlight .m { color: #666666 } /* Literal.Number */
        .highlight .s { color: #BA2121 } /* Literal.String */
        .highlight .na { color: #687822 } /* Name.Attribute */
        .highlight .nb { color: #008000 } /* Name.Builtin */
        .highlight .nc { color: #0000FF; font-weight: bold } /* Name.Class */
        .highlight .no { color: #880000 } /* Name.Constant */
        .highlight .nd { color: #AA22FF } /* Name.Decorator */
        .highlight .ni { color: #999999; font-style: italic } /* Name.Entity */
        .highlight .ne { color: #D2413A; font-weight: bold } /* Name.Exception */
        .highlight .nf { color: #0000FF } /* Name.Function */
        .highlight .nl { color: #A0A000 } /* Name.Label */
        .highlight .nn { color: #0000FF; font-weight: bold } /* Name.Namespace */
        .highlight .nt { color: #008000; font-weight: bold } /* Name.Tag */
        .highlight .nv { color: #19177C } /* Name.Variable */
        .highlight .ow { color: #AA22FF; font-weight: bold } /* Operator.Word */
        .highlight .w { color: #bbbbbb } /* Text.Whitespace */
        .highlight .mf { color: #666666 } /* Literal.Number.Float */
        .highlight .mh { color: #666666 } /* Literal.Number.Hex */
        .highlight .mi { color: #666666 } /* Literal.Number.Integer */
        .highlight .mo { color: #666666 } /* Literal.Number.Oct */
        .highlight .sb { color: #BA2121 } /* Literal.String.Backtick */
        .highlight .sc { color: #BA2121 } /* Literal.String.Char */
        .highlight .sd { color: #BA2121; font-style: italic } /* Literal.String.Doc */
        .highlight .s2 { color: #BA2121 } /* Literal.String.Double */
        .highlight .se { color: #BB6622; font-weight: bold } /* Literal.String.Escape */
        .highlight .sh { color: #BA2121 } /* Literal.String.Heredoc */
        .highlight .si { color: #BB6688; font-weight: bold } /* Literal.String.Interpol */
        .highlight .sx { color: #008000 } /* Literal.String.Other */
        .highlight .sr { color: #BB6688 } /* Literal.String.Regex */
        .highlight .s1 { color: #BA2121 } /* Literal.String.Single */
        .highlight .ss { color: #19177C } /* Literal.String.Symbol */
        .highlight .bp { color: #008000 } /* Name.Builtin.Pseudo */
        .highlight .vc { color: #19177C } /* Name.Variable.Class */
        .highlight .vg { color: #19177C } /* Name.Variable.Global */
        .highlight .vi { color: #19177C } /* Name.Variable.Instance */
        .highlight .il { color: #666666 } /* Literal.Number.Integer.Long */
    </style>
    """
    return style + html
