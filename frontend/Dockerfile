FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build for production
RUN npm run build

EXPOSE 3000

# Serve built files
CMD ["npx", "serve", "-s", "dist", "-l", "3000"]
