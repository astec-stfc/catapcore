# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "catapcore"
copyright = "2026, STFC Accelerator Science and Technology Centre"
author = "STFC Accelerator Science and Technology Centre"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = []
html_logo = None
html_theme_options = {
    "canonical_url": "https://astec-stfc.github.io/catapcore/",
    "analytics_id": "",
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_external_links": False,
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

# -- Options for autodoc extensions ------------------------------------------

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": False,
    "show-inheritance": True,
    "inherited-members": True,
}

# Show type hints in documentation
autodoc_typehints = "description"

# set options for pydantic models
autodoc_pydantic_model_show_json = False  # don't include JSON schema for pydantic models
autodoc_pydantic_model_show_field_summary = (
    True  # don't include a bullet-point list of model fields
)
autodoc_pydantic_model_show_config_summary = (
    False  # don't include model configurations for pydantic models
)
autodoc_pydantic_field_list_validators = True  # don't list validators for pydantic model fields
autodoc_pydantic_field_show_constraints = False  # don't list constraints for pydantic model fields
autodoc_pydantic_model_show_validator_summary = (
    False  # dont' include validator methods for pydantic models
)
autodoc_pydantic_model_show_validator_members = (
    False  # don't include documentation for validator methods
)
autodoc_pydantic_field_doc_policy = "both"  # shows docstrings and Field descriptions
# autodoc_typehints = "none"

autodoc_mock_imports = [
    # "laura.models.elementList",  # or whichever module fails
    "pydantic",  # mock dependencies if needed
]

# -- Napoleon configuration --------------------------------------------------

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Intersphinx configuration -----------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pydantic": ("https://docs.pydantic.dev/latest", None),
}
