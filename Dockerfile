# Simple Dockerfile that mirrors local development
FROM node:18

# Install Python and pip (Node.js image already has Python3)
RUN apt-get update && apt-get install -y python3-pip python3-venv && rm -rf /var/lib/apt/lists/*

# Install pnpm globally
RUN npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy everything
COPY . .

# Create and activate virtual environment, then install Python dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install -r back/requirements.txt

# Install frontend dependencies
WORKDIR /app/front
RUN pnpm install

# Go back to root
WORKDIR /app

# Make the backend script executable
RUN chmod +x run_python_backend.sh

# Create a simple startup script
RUN echo '#!/bin/bash\n\
cd /app/front && pnpm dev --hostname 0.0.0.0 &\n\
cd /app && ./run_python_backend.sh &\n\
wait' > /app/start.sh && chmod +x /app/start.sh

# Expose ports
EXPOSE 3000 8000

# Start both services
CMD ["/app/start.sh"]
