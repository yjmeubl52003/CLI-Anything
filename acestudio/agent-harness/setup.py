#!/usr/bin/env python3
"""setup.py for cli-anything-acestudio."""

from setuptools import find_namespace_packages, setup


with open("cli_anything/acestudio/README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name="cli-anything-acestudio",
    version="1.0.0",
    author="cli-anything contributors",
    author_email="",
    description="CLI harness for ACE Studio via the official local MCP server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HKUDS/CLI-Anything",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[],
    extras_require={
        "repl": [
            "prompt-toolkit>=3.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-acestudio=cli_anything.acestudio.acestudio_cli:main",
        ],
    },
    package_data={
        "cli_anything.acestudio": ["skills/*.md"],
    },
    include_package_data=True,
    zip_safe=False,
)
