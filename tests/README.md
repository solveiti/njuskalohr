# Tests Directory

This directory contains all test files and demo scripts for the Njuskalo HR stealth publish system.

## Test Files

- `test_stealth_publish.py` - Main stealth publishing system tests
- `test_form_filling.py` - Form filling functionality tests
- `test_ad_status_validation.py` - Ad status validation tests
- `test_login.py` - Login functionality tests
- `test_firefox_tunel.py` - Firefox tunnel configuration tests

## Demo Files

- `demo_form_filling_complete.py` - Complete form filling demonstration
- `demo_status_validation.py` - Status validation demonstration

## Running Tests

From the project root directory:

```bash
# Run a specific test
python tests/test_stealth_publish.py

# Run form filling tests
python tests/test_form_filling.py

# Run demos
python tests/demo_form_filling_complete.py
```

## Note

This directory is ignored by git (added to `.gitignore`) to prevent test files from being committed to the repository.
