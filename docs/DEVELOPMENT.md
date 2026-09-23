# Developer Guide & Engineering Standards

## 1. Development Environment Setup

### 1.1 Requirements
- Python 3.12+
- FFmpeg 6.0+ with `libass` and `libx264` enabled
- Git 2.30+

### 1.2 Virtual Environment Setup
```bash
# Clone the repository (if not already cloned)
# Navigate to project root
python -m venv .venv

# Activate environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.3 Setting Up Environment Variables
```bash
copy .env.example .env
```
Fill in the credentials for Google Drive, Gemini API, YouTube OAuth, and SMTP.

---

## 2. Coding Standards & Conventions

### 2.1 Code Formatting
- PEP 8 compliance enforced via `flake8` and `black`.
- Maximum line length: 100 characters.
- Strict type hinting using Python's `typing` module or modern built-in generics (`list[str]`, `dict[str, Any]`).

### 2.2 Logging Conventions
- Never use raw `print()` statements in module code.
- Always use the structured logger:
  ```python
  from src.logging_config import get_logger

  logger = get_logger(component="PrivacyGuard")
  logger.info("Scanning frame for sensitive data", extra_data={"frame_idx": 142})
  ```

### 2.3 Error Handling Conventions
- Always raise or wrap in custom exceptions from `src.exceptions`:
  ```python
  from src.exceptions import PipelineError

  raise PipelineError(
      operation="download_video",
      component="DriveIngestion",
      file_path=str(dest_path),
      root_cause=str(err),
      recovery_action="Check network connectivity and Google Drive folder permissions.",
      status="FAILED"
  )
  ```

---

## 3. Running Tests

Run the full test suite with coverage:
```bash
python -m pytest tests/ -v
```

Run specific test modules:
```bash
python -m pytest tests/test_config.py
python -m pytest tests/test_exceptions.py
```

---

## 4. Git Commit Guidelines

Before committing:
1. Verify `git status` to ensure no sensitive files (`.env`, `credentials.json`, `token.json`) are staged.
2. Run test suite: `pytest tests/`.
3. Check code formatting: `black --check src/ tests/`.
4. Commit using conventional commit format:
   - `feat: add OCR bounding box detection`
   - `fix: correct audio ducking volume levels`
   - `docs: update YouTube OAuth guide`
