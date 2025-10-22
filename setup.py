from setuptools import setup, find_packages

setup(
    name="trading-bot",
    version="1.0.0",
    description="A sophisticated trading bot with backtesting capabilities",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "flask==2.3.3",
        "pandas==2.1.1",
        "numpy==1.24.3",
        "plotly==5.17.0",
        "yfinance==0.2.18",
        "requests==2.31.0",
        "python-dotenv==1.0.0",
        "click==8.1.7",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "trading-bot=main:app",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
