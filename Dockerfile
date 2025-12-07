# Use .NET SDK 9.0 image (MoonsecDeobfuscator requires .NET 9.0)
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build

# Install git (needed to clone source if not present)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files first
COPY bot.py requirements.txt Dockerfile ./

# Download MoonsecDeobfuscator source if src folder doesn't exist
# If you've already included src/ in your repo, this will be skipped
RUN if [ ! -d "src" ]; then \
        echo "Downloading MoonsecDeobfuscator source code..." && \
        git clone https://github.com/0ese/Mun-deobf.git src; \
    else \
        echo "Using existing src/ folder"; \
    fi

# Build the Moonsec Deobfuscator
WORKDIR /app/src
RUN dotnet restore && dotnet build -c Release

# Find the built executable (supports multiple .NET versions)
RUN find /app/src/bin/Release -name "MoonsecDeobfuscator" -type f -executable | head -1 > /tmp/exe_path || true
RUN find /app/src/bin/Release -name "MoonsecDeobfuscator.dll" | head -1 > /tmp/dll_path || true

# Runtime stage
FROM mcr.microsoft.com/dotnet/runtime:9.0

# Install Python 3 and pip
RUN apt-get update && apt-get install -y python3 python3-pip findutils && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built binaries from build stage
COPY --from=build /app/src/bin/Release ./bin/

# Copy Python bot files
COPY bot.py ./
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Verify src folder exists (from build stage)
COPY --from=build /app/src ./src

# Run the Discord bot
CMD ["python3", "bot.py"]


