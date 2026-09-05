FROM node:20-slim

WORKDIR /app

# Copy package descriptors
COPY package*.json ./

# Install project dependencies
RUN npm install

# Copy application source
COPY . .

# Build application
RUN npm run build

# Cloud Run defaults to PORT 8080
ENV PORT=8080
EXPOSE 8080

# Serve application via preview
CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port ${PORT:-8080}"]
