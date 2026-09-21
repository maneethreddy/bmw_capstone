# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# ---------------------------------------------------------------------------
# Path setup — point Sphinx at the project root so autodoc can import modules
# ---------------------------------------------------------------------------

# The project root is one level above this file (docs/)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Project information
# ---------------------------------------------------------------------------

project = "BMW Capstone P11"
copyright = "2024, BMW Capstone P11 Team"
author = "BMW Capstone P11 Team"
release = "0.1.0"

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",          # Core: pull docstrings from Python source
    "sphinx.ext.napoleon",         # Support Google & NumPy style docstrings
    "sphinx.ext.viewcode",         # Add [source] links to each symbol
    "sphinx.ext.intersphinx",      # Cross-link to external docs (Python, boto3…)
    "sphinx.ext.autosummary",      # Generate summary tables for packages
    "sphinx_autodoc_typehints",    # Render type annotations in autodoc output
    "myst_parser",                 # Allow Markdown files alongside RST
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ---------------------------------------------------------------------------
# Autodoc settings
# ---------------------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": False,
    "special-members": "__init__",
    "show-inheritance": True,
}

# Put type hints only in the description (not duplicated in the signature)
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Napoleon (Google / NumPy docstring parser)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_admonition_for_examples = True
napoleon_use_ivar = True

# ---------------------------------------------------------------------------
# Intersphinx mapping — external cross-references
# ---------------------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "boto3": ("https://boto3.amazonaws.com/v1/documentation/api/latest", None),
}

# Suppress noisy warnings from sphinx-autodoc-typehints resolving PySpark
# internal typing stubs (pyspark._typing, pyspark.sql._typing, numpy).
suppress_warnings = [
    "sphinx_autodoc_typehints.forward_reference",
    "sphinx_autodoc_typehints.guarded_import",
]

# ---------------------------------------------------------------------------
# HTML output — Furo theme
# ---------------------------------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_title = "BMW Capstone P11 Docs"

html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "light_css_variables": {
        "color-brand-primary": "#1c69d4",      # BMW blue
        "color-brand-content": "#1c69d4",
    },
    "dark_css_variables": {
        "color-brand-primary": "#4f9ef8",
        "color-brand-content": "#4f9ef8",
    },
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/your-org/bmw_capstone_p11",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0"
                     viewBox="0 0 16 16" height="1em" width="1em"
                     xmlns="http://www.w3.org/2000/svg">
                  <path fill-rule="evenodd"
                    d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59
                       .4.07.55-.17.55-.38
                       0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94
                       -.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53
                       .63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
                       .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95
                       0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12
                       0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27
                       .68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82
                       .44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15
                       0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
                       0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38
                       A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
                </svg>
            """,
            "class": "",
        },
    ],
}

# Autosummary — automatically generate stub RST files
autosummary_generate = True
