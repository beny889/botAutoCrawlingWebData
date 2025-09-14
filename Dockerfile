# Production Docker Configuration for Andalan ATK Backend Export Automation
# Optimized Chrome installation with Selenium WebDriver integration
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies for Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy automation scripts and shared components
COPY main_scheduler.py .
COPY single_session_automation.py .
COPY exports/ ./exports/
COPY shared/ ./shared/
COPY service-account-key.json .

# Create downloads directory
RUN mkdir -p downloads

# Set environment variables for headless Chrome
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV CHROME_PATH=/usr/bin/google-chrome-stable

# Production automation execution
CMD ["python", "main_scheduler.py", "--all", "--headless", "--production", "--single-session"]