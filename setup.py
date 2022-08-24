
import datetime
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "pydcam",
    version = "2022.08.24",
    author = "David Jenkins",
    author_email = "David.Jenkins@eso.org",
    description = "A python interface for Hamamatsu Cameras",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/david-jenkins/pydcam",
    project_urls = {
        "Bug Tracker" : "https://github.com/david-jenkins/pydcam/issues",
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "Operating System :: Windows",
    ],
    packages = setuptools.find_packages(where="."),
    package_dir = {"":"."},
    python_requires = ">=3.7",
    install_requires=[
          'numpy',
          'PyQt5',
          'pyqtgraph',#@git+https://github.com/pyqtgraph/pyqtgraph',
          'pyzmq',
          'astropy',
          'toml',
          'h5py',
          'orjson',
          'pysinewave@git+https://github.com/david-jenkins/pysinewave',
          'superqt@git+https://github.com/napari/superqt',
      ],
    # dependency_links=[
    #     'git+git://github.com/pyqtgraph/pyqtgraph.git@master',
    #     'git+git://github.com/david-jenkins/pysinewave.git@master'],
    entry_points = {
        "console_scripts": [
            "dcam_gui=pydcam.bin:gui",
            "dcam_reader=pydcam.bin:reader",
            "dcam_saver=pydcam.bin:saver",
            "dcam_display=pydcam.bin:display",
                            ],
    },
)


