# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PyReadCam'
copyright = '2023, David Jenkins'
author = 'David Jenkins'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'autoapi.extension',
]

autosummary_generate = True

autoapi_root = "autoapi"
autoapi_dirs = ["../../pydcam"]
autoapi_type = 'python'
autoapi_template_dir = '_autoapi_templates'
autoapi_add_toctree_entry = False
autoapi_keep_files = True
autoapi_generate_api_docs = True

modindex_common_prefix = ["pydcam."]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_logo = '_static/camera.png'
html_favicon = '_static/camera.png'

html_static_path = ['_static']

html_theme_options = {
  "logo": {
      "image_light": "camera.png",
      "image_dark": "camera.png",
      "text": "PyReadCam",
  },
  "github_url": "https://github.com/david-jenkins/pydcam",
  "collapse_navigation": True,
#   "external_links": [
#       {"name": "Learn", "url": "https://doi.org/10.1117/12.2629590"}
#       ],
  # Add light/dark mode and documentation version switcher:
  "navbar_end": ["theme-switcher"],# "version-switcher", "navbar-icon-links"],
  "icon_links" : [],
#   "switcher": {
#       "version_match": switcher_version,
#       "json_url": "https://numpy.org/doc/_static/versions.json",
#   },
}


latex_engine = 'pdflatex'
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    'extraclassoptions': 'openany,oneside',
    }