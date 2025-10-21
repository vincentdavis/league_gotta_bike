FROM ghcr.io/astral-sh/uv:python3.13-alpine

# Install Node.js and npm for Tailwind CSS build
RUN apk add --no-cache nodejs npm

# Create and change to the app directory.
WORKDIR /app

# Copy local code to the container image.
COPY . .

# Install project dependencies.
RUN uv sync --frozen

# Entrypoint script to handle migrations, collectstatic, and start the app.
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run the app using the script.
CMD ["/app/entrypoint.sh"]
