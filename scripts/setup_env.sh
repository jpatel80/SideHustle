#!/bin/bash
# Setup script for the cloud environment (runs when a session's container is built).
# Installs the Python packages the repo scripts need and the PDF tools used for validation.
set -e
if [ -d SideHustle ]; then
  pip install -q -r SideHustle/requirements.txt
fi
command -v pdffonts >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq poppler-utils)
