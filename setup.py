#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read requirements from file
def read_requirements():
    with open("requirements.txt", "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read long description from README
def read_readme():
    if os.path.exists("README.md"):
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    return ""

setup(
    name="wems-mcp-server",
    version="1.0.0",
    author="Helios",
    author_email="heliosarchitectlbf@gmail.com",
    description="World Event Monitoring System - MCP server for natural hazard monitoring",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/loverbearfarm/wems-mcp-server",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "wems=wems_mcp_server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.md", "*.txt"],
    },
    keywords=[
        "mcp", "model-context-protocol", "natural-disasters", "earthquake", 
        "tsunami", "volcano", "solar-weather", "monitoring", "alerts", 
        "webhooks", "usgs", "noaa", "ai", "automation"
    ],
    project_urls={
        "Bug Reports": "https://github.com/loverbearfarm/wems-mcp-server/issues",
        "Source": "https://github.com/loverbearfarm/wems-mcp-server",
        "Documentation": "https://github.com/loverbearfarm/wems-mcp-server#readme",
    },
)