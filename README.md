# CatGPT Backend

This document explains how to set up and run the Python app locally for development purposes.

This is not recommended. Instead the Dockerized setup described in [CatGPT](https://github.com/catgpt-9498344583/catgpt) should be used.

## Prerequisites

- Python - 3.13.7
- `pip` - 25.2
- `virtualenv` (optional but recommended)
- `pytest` - 9.0.1
- `pylint` - 3.3.9
- `git` - 2.52.0

## 1. Clone the Repository

```bash
git clone https://github.com/catgpt-9498344583/backend.git
cd backend
```

## 2. Set Up a Virtual Environment

It's recommended to use a virtual environment to isolate dependencies:

### Create a virtual environment in the 'env' folder
```bash
python -m venv env
```

### Activate the virtual environment
#### Linux / macOS
```bash
source env/bin/activate
```
#### Windows (PowerShell)
```ps1
.\env\Scripts\Activate.ps1
```

## 3. Install Dependencies

Install the required Python packages from requirements.txt:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configure Environment Variables

The app uses a `.env` file for environment-specific configuration. Make sure `.env` exists in the project root:

### Example .env
```
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=YOUR_DEFAULT_REGION
AGENT_ID=YOUR_AGENT_ID
AGENT_ALIAS_ID=YOUR_ALIAS_ID
```

Modify any variables as needed.
## 5. Run the App

You can run the application with:

```bash
python run.py
```

By default, the app will start in development mode.
## 6. Running Tests

Tests are located in the tests folder. Run them using pytest:

```bash
PYTHONPATH=. pytest tests/
```

## 7. Linting
```bash
pylint . --ignore env
```

## 8. Project Structure

```
.
├── app/               # Main application code
├── static/            # Static website assets
├── tests/             # Test suite
├── training_data/     # Data used for training or processing
├── run.py             # App entry point
├── requirements.txt   # Python dependencies
├── .env               # Environment variables
├── README.md          # This file
└── env/               # Virtual environment folder
```

## 9. Notes

    Do not commit the env/ or .env files to version control.

    For any changes to dependencies, update requirements.txt using:

```bash
pip freeze > requirements.txt
```
