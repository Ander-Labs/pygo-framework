#!/bin/bash
# PyGo Universal Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/PyGo-Labs/pygo-framework/main/install.sh | bash

set -e

# Configuration
PYGO_VERSION="${PYGO_VERSION:-latest}"
PYGO_REPO="PyGo-Labs/pygo-framework"
PYGO_BIN="pygo"

# Colors (PyGo palette)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

detect_platform() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    
    case "$OS" in
        Linux*)  OS=linux ;;
        Darwin*) OS=darwin ;;
        CYGWIN*|MINGW*|MSYS*) OS=windows ;;
        *) echo -e "${RED}Unsupported OS: $OS${NC}"; exit 1 ;;
    esac
    
    case "$ARCH" in
        x86_64|amd64) ARCH=amd64 ;;
        aarch64|arm64) ARCH=arm64 ;;
        armv7l) ARCH=arm ;;
        *) echo -e "${RED}Unsupported architecture: $ARCH${NC}"; exit 1 ;;
    esac
    
    echo -e "${GREEN}Detected platform: ${OS}/${ARCH}${NC}"
}

get_latest_version() {
    if [ "$PYGO_VERSION" = "latest" ]; then
        # Get the latest release tag using GitHub API (fall back to releases page)
        PYGO_VERSION=$(curl -sL "https://api.github.com/repos/$PYGO_REPO/releases/latest" | grep '"tag_name"' | head -1 | sed -E 's/.*"tag_name": *"v?([^"]+)".*/\1/')
        if [ -z "$PYGO_VERSION" ]; then
            echo -e "${RED}Failed to get latest version${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}Version: v$PYGO_VERSION${NC}"
}

download_binary() {
    VERSION_TAG="v$PYGO_VERSION"
    local BINARY_NAME="${PYGO_BIN}_${VERSION_TAG}_${OS}_${ARCH}"
    local DOWNLOAD_URL="https://github.com/$PYGO_REPO/releases/download/${VERSION_TAG}/${PYGO_BIN}_${VERSION_TAG}_${OS}_${ARCH}.tar.gz"
    
    echo -e "${YELLOW}Downloading PyGo v${PYGO_VERSION}...${NC}"
    
    if [ "$OS" = "windows" ]; then
        DOWNLOAD_URL="https://github.com/$PYGO_REPO/releases/download/${VERSION_TAG}/${PYGO_BIN}_${VERSION_TAG}_${OS}_${ARCH}.zip"
        TEMP_DIR=$(mktemp -d)
        curl -fsSL "$DOWNLOAD_URL" -o "$TEMP_DIR/pygo.zip" || {
            echo -e "${RED}Download failed. Check your internet connection.${NC}"
            exit 1
        }
        unzip -o "$TEMP_DIR/pygo.zip" -d "$TEMP_DIR"
        mv "$TEMP_DIR/$PYGO_BIN.exe" "/tmp/$PYGO_BIN.exe"
        INSTALL_PATH="/tmp/$PYGO_BIN.exe"
    else
        TEMP_DIR=$(mktemp -d)
        curl -fsSL "$DOWNLOAD_URL" -o "$TEMP_DIR/pygo.tar.gz" || {
            echo -e "${RED}Download failed. Check your internet connection.${NC}"
            exit 1
        }
        tar -xzf "$TEMP_DIR/pygo.tar.gz" -C "$TEMP_DIR" 2>/dev/null || tar -xzf "$TEMP_DIR/pygo.tar.gz" -C "$TEMP_DIR" --strip-components=0
        INSTALL_PATH="$TEMP_DIR/$PYGO_BIN"
    fi
    
    echo -e "${GREEN}Download complete${NC}"
}

install_binary() {
    local INSTALL_DIR
    
    if [ "$OS" = "windows" ]; then
        INSTALL_DIR="$USERPROFILE/bin"
        mkdir -p "$INSTALL_DIR"
        mv "/tmp/$PYGO_BIN.exe" "$INSTALL_DIR/$PYGO_BIN.exe"
        INSTALL_PATH="$INSTALL_DIR/$PYGO_BIN.exe"
    else
        INSTALL_DIR="/usr/local/bin"
        if [ ! -w "$INSTALL_DIR" ]; then
            INSTALL_DIR="$HOME/.local/bin"
            mkdir -p "$INSTALL_DIR"
        fi
        mv "$INSTALL_PATH" "$INSTALL_DIR/$PYGO_BIN"
        INSTALL_PATH="$INSTALL_DIR/$PYGO_BIN"
    fi
    
    chmod +x "$INSTALL_PATH"
    echo -e "${GREEN}Installed to: $INSTALL_PATH${NC}"
}

verify_installation() {
    echo -e "${YELLOW}Verifying installation...${NC}"
    
    if command -v "$PYGO_BIN" &> /dev/null; then
        echo -e "${GREEN}Success! $PYGO_BIN is ready.${NC}"
    else
        echo -e "${RED}Installation failed. $PYGO_BIN not found in PATH.${NC}"
        echo -e "${YELLOW}Try adding to your PATH: export PATH=\$PATH:$INSTALL_DIR${NC}"
        exit 1
    fi
}

cleanup() {
    rm -rf "$TEMP_DIR" 2>/dev/null || true
}

main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  PyGo Universal Installer${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    detect_platform
    get_latest_version
    download_binary
    install_binary
    verify_installation
    cleanup
    
    echo -e ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e ""
    echo -e "Next steps:"
    echo -e "  1. Run: ${YELLOW}pygo doctor${NC} to verify your environment"
    echo -e "  2. Run: ${YELLOW}pygo new my-app${NC} to create a new project"
    echo -e "  3. Visit: ${YELLOW}https://pygo-docs.vercel.app/${NC} for documentation"
    echo -e ""
}

main "$@"
