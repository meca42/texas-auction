#!/bin/bash
# Install Chrome for Selenium in Render environment

# Create a directory for Chrome
mkdir -p /opt/render/project/chrome

# Download and install Chrome
cd /opt/render/project/chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get update
apt-get install -y ./google-chrome-stable_current_amd64.deb

# Set Chrome path for the application
export CHROME_PATH=/opt/render/project/chrome/google-chrome-stable

# Create a symlink to make it easier to find
ln -s /usr/bin/google-chrome-stable /usr/bin/chrome

# Print Chrome version to verify installation
google-chrome-stable --version
