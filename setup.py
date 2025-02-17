from setuptools import setup, find_packages

setup(
    name="travel-agent",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "pandas",
        "plotly",
        "fpdf",
        "openpyxl"
    ],
)
