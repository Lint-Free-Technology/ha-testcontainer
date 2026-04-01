# custom_components/
#
# This directory is mounted as /config/custom_components/ inside the
# Home Assistant test container.
#
# Populate it by running the generic fetch script for any component:
#
#   python scripts/fetch_component.py owner/repo            # latest release
#   python scripts/fetch_component.py owner/repo 5.3.1      # specific version
#   python scripts/fetch_component.py owner/repo --list     # list releases
#
# Examples:
#
#   python scripts/fetch_component.py Lint-Free-Technology/uix
#   python scripts/fetch_component.py custom-cards/button-card
#
# Or use make:
#
#   make setup                                    # default: Lint-Free-Technology/uix
#   make setup COMPONENT=custom-cards/button-card
#   make setup COMPONENT=Lint-Free-Technology/uix VERSION=5.3.1
#
# Or point HATestContainer at a different directory:
#
#   HATestContainer(custom_components_path="/path/to/your/custom_components")
#
# Files in this directory are intentionally excluded from git (see .gitignore).
# Only this README is committed so the directory exists in the repository.
