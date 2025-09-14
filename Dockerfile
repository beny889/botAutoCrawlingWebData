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

# Install Python dependencies with verbose output
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt --verbose

# Verify critical dependencies are installed
RUN python -c "import selenium; print(f'Selenium version: {selenium.__version__}')"
RUN python -c "import pandas; print(f'Pandas version: {pandas.__version__}')"
RUN python -c "import gspread; print('Google Sheets API: OK')"

# Copy automation scripts and shared components
COPY main_scheduler.py .
COPY single_session_automation.py .
COPY exports/ ./exports/
COPY shared/ ./shared/
# Note: service-account-key.json will be created from environment variable at runtime

# Create downloads directory
RUN mkdir -p downloads

# Set environment variables for headless Chrome
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV CHROME_PATH=/usr/bin/google-chrome-stable

# Create startup script for service account setup
RUN echo '#!/bin/bash\n\
if [ -n "$GOOGLE_SERVICE_ACCOUNT_JSON" ]; then\n\
    echo "$GOOGLE_SERVICE_ACCOUNT_JSON" > /app/service-account-key.json\n\
    echo "Service account key created from environment variable"\n\
else\n\
    echo "Warning: GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set"\n\
fi\n\
exec python main_scheduler.py --all --headless --production --single-session\n' > /app/start.sh

RUN chmod +x /app/start.sh

# Production automation execution with service account setup
CMD ["/app/start.sh"]