# ==============================================================================
# Stage 1: Build Frontend Assets
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency definitions
COPY package.json package-lock.json ./

# Install dependencies using clean install
RUN npm ci

# Copy source code and build production bundle
COPY . .
RUN npm run build

# ==============================================================================
# Stage 2: Serve with Lightweight Nginx
# ==============================================================================
FROM nginx:1.25-alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx configuration for SPA routing & reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built production assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
