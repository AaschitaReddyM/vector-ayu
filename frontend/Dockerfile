FROM node:20-slim

WORKDIR /app

# Copy package descriptors
COPY package*.json ./

# Install project dependencies
RUN npm install

# Copy application source
COPY . .

# Cloud Run defaults to PORT 8080
ENV PORT=8080
EXPOSE 8080

# Run Vite server directly
CMD ["sh", "-c", "npm run dev -- --host 0.0.0.0 --port ${PORT:-8080}"]
