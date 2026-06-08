# IELTS Skills Automation

A specialized repository for generating, validating, and curating 100% compliant IELTS mock tests.

## Purpose
The primary objective of this project is to provide a robust framework for generating IELTS reading and listening tests using AI models. By enforcing strict programmatic rules and providing well-curated example specifications, we can achieve high-quality, exam-standard content.

## Features
- **Strict Compliance**: Enforces core IELTS mechanics like the Synonym Rule and the Needle-in-Passage Rule.
- **Automated Validation**: A comprehensive Python validator (`scripts/validate.py`) ensures all tests meet length, format, and semantic guidelines, including word count constraints and boolean question distribution.
- **Topic Diversity**: Curated topic banks to prevent repetition in reading and listening materials.
- **Synonym Bank**: A curated list of 150+ academic synonym pairs to prevent exact word repetition between passages and questions.

## Repository Structure
- `references/`: Project specs and synonym banks.
- `scripts/`: Validation and automation tools (`validate.py`).
- `examples/`: Perfect template models for Reading and Listening.
- `demo/`: Generated test instances for testing and validation.

## Usage
Run the validation script against any generated Markdown test to ensure it meets the IELTS specification:
```bash
python3 scripts/validate.py path/to/your/test.md
```
