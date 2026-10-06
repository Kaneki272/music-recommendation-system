FROM node:20-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the Vite application
RUN npm run build

# Install a simple static file server
RUN npm install -g serve

# Expose port 3000
EXPOSE 3000

# Start the server with SPA routing fallback (-s)
CMD ["serve", "-s", "dist", "-l", "3000"]
