from setuptools import setup, find_packages

setup(
    name="travel-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.29.0",
        "pandas>=1.3.0",
        "numpy>=1.19.3",
        "requests>=2.27.0",
        "python-dateutil>=2.7.3",
    ],
    python_requires=">=3.9",
)
