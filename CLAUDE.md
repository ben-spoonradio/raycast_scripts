# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raycast practical exam training tool that consists of:
- A Python curses-based terminal UI for practice sessions
- A bash script for managing code review output and storage

## Running the Application

```bash
# Run the Raycast exam terminal UI
python raycast_exam_terminal_ui.py
```

The terminal UI provides a 5-minute timed practice session with 6 Raycast tasks that users can navigate with arrow keys and mark as completed with Enter.

## Code Review Workflow

The project includes a review management system:

```bash
# Generate and display code review (requires code_review_feedback.md to exist)
./show_review.sh
```

This script:
- Creates timestamped review files in `reviews/` directory
- Uses git commit hash and project name for unique filenames
- Displays reviews with syntax highlighting (via `bat` if available)

## Architecture Notes

- **raycast_exam_terminal_ui.py**: Single-file curses application with centered text rendering utilities
- **show_review.sh**: Bash utility for review file management with git integration
- **reviews/**: Directory containing timestamped markdown review files

## File Naming Convention

Review files follow the pattern: `{project_name}_{commit_hash}_{YYYYMMDD_HHMM}.md`

## Dependencies

- Python with curses library (standard library)
- Git (for commit hash extraction)
- Optional: `bat` for enhanced syntax highlighting