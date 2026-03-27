# custom_components/
#
# This directory is mounted as /config/custom_components/ inside the
# Home Assistant test container.
#
# Populate it by running:
#
#   python scripts/fetch_uix.py            # download latest UIX release
#   python scripts/fetch_uix.py 5.3.1      # download a specific version
#
# Or point HATestContainer at a different directory:
#
#   HATestContainer(custom_components_path="/path/to/your/custom_components")
#
# Files in this directory are intentionally excluded from git (see .gitignore).
# Only this README is committed so the directory exists in the repository.
