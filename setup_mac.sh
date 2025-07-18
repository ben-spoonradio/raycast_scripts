#!/bin/bash

# Raycast Scripts macOS Setup Script
# This script installs all dependencies needed to run the Raycast scripts

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Raycast Scripts macOS Setup"
echo "=============================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script is designed for macOS only.${NC}"
    exit 1
fi

# Check if Homebrew is installed
echo "📍 Checking Homebrew..."
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew is not installed. Installing now...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo -e "${GREEN}✓ Homebrew is already installed${NC}"
fi

# Install Python 3.10 via Homebrew
echo ""
echo "📍 Installing Python 3.10 via Homebrew..."
if brew list python@3.10 &> /dev/null; then
    echo -e "${GREEN}✓ Python 3.10 is already installed${NC}"
else
    echo -e "${YELLOW}Installing Python 3.10...${NC}"
    brew install python@3.10
fi

# Get Python 3.10 path
if [[ -f "/opt/homebrew/bin/python3.10" ]]; then
    PYTHON_PATH="/opt/homebrew/bin/python3.10"
elif [[ -f "/usr/local/bin/python3.10" ]]; then
    PYTHON_PATH="/usr/local/bin/python3.10"
else
    echo -e "${RED}Error: Could not find Python 3.10 installation.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3.10 found at: $PYTHON_PATH${NC}"

# Configure .zshrc with Python alias
echo ""
echo "📍 Configuring Python alias in .zshrc..."
ZSHRC="$HOME/.zshrc"

# Check if alias already exists with the correct path
EXISTING_PYTHON_ALIAS=$(grep "^alias python=" "$ZSHRC" 2>/dev/null | grep -o "'.*'" | tr -d "'")
EXISTING_PYTHON3_ALIAS=$(grep "^alias python3=" "$ZSHRC" 2>/dev/null | grep -o "'.*'" | tr -d "'")

if [[ "$EXISTING_PYTHON_ALIAS" == "$PYTHON_PATH" ]] && [[ "$EXISTING_PYTHON3_ALIAS" == "$PYTHON_PATH" ]]; then
    echo -e "${GREEN}✓ Python aliases already correctly configured in .zshrc${NC}"
else
    # Remove old aliases if they exist
    if grep -q "^alias python=" "$ZSHRC" 2>/dev/null || grep -q "^alias python3=" "$ZSHRC" 2>/dev/null; then
        echo -e "${YELLOW}Updating existing Python aliases...${NC}"
        sed -i '' '/^alias python=/d' "$ZSHRC"
        sed -i '' '/^alias python3=/d' "$ZSHRC"
        # Also remove the comment line if it exists
        sed -i '' '/# Python 3.10 alias (added by Raycast Scripts setup)/d' "$ZSHRC"
    fi
    
    # Add new aliases
    echo "" >> "$ZSHRC"
    echo "# Python 3.10 alias (added by Raycast Scripts setup)" >> "$ZSHRC"
    echo "alias python='$PYTHON_PATH'" >> "$ZSHRC"
    echo "alias python3='$PYTHON_PATH'" >> "$ZSHRC"
    echo -e "${GREEN}✓ Added Python alias to .zshrc${NC}"
fi

# Source .zshrc for current session
source "$ZSHRC"

# Update PATH for current script execution
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Verify Python version
echo ""
echo "📍 Verifying Python installation..."
PYTHON_VERSION=$($PYTHON_PATH -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓ Python $PYTHON_VERSION is configured${NC}"

# Check if pip is installed
echo ""
echo "📍 Checking pip..."
if ! $PYTHON_PATH -m pip --version &> /dev/null; then
    echo -e "${YELLOW}pip is not installed. Installing now...${NC}"
    $PYTHON_PATH -m ensurepip --upgrade
else
    echo -e "${GREEN}✓ pip is already installed${NC}"
fi

# Function to check if a Python package is installed
check_python_package() {
    $PYTHON_PATH -c "import $1" 2>/dev/null
}

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

echo ""
echo "🔧 Installing dependencies..."
echo ""

# Core dependencies for Raycast exam tool
echo "📦 Installing core Python packages..."
CORE_PACKAGES=("pandas" "openpyxl")
for package in "${CORE_PACKAGES[@]}"; do
    if check_python_package "$package"; then
        echo -e "  ${GREEN}✓ $package is already installed${NC}"
    else
        echo -e "  ${YELLOW}Installing $package...${NC}"
        $PYTHON_PATH -m pip install "$package"
    fi
done

# Optional dependencies
echo ""
echo "📦 Installing optional dependencies..."
echo "Would you like to install optional dependencies for additional features? (y/n)"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    
    # Audio processing
    echo ""
    echo "🎵 Audio Processing Features:"
    echo "Install ffmpeg for audio conversion? (y/n)"
    read -r audio_response
    if [[ "$audio_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if command_exists ffmpeg; then
            echo -e "  ${GREEN}✓ ffmpeg is already installed${NC}"
        else
            echo -e "  ${YELLOW}Installing ffmpeg...${NC}"
            brew install ffmpeg
        fi
    fi
    
    # Speech recognition
    echo ""
    echo "🎤 Speech Recognition Features:"
    echo "Install packages for speech recognition and transcription? (y/n)"
    read -r speech_response
    if [[ "$speech_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        SPEECH_PACKAGES=("pyperclip" "openai-whisper" "anthropic" "pyaudio")
        for package in "${SPEECH_PACKAGES[@]}"; do
            if check_python_package "$package"; then
                echo -e "  ${GREEN}✓ $package is already installed${NC}"
            else
                echo -e "  ${YELLOW}Installing $package...${NC}"
                if [[ "$package" == "pyaudio" ]]; then
                    # pyaudio requires portaudio
                    if ! command_exists portaudio; then
                        brew install portaudio
                    fi
                fi
                $PYTHON_PATH -m pip install "$package"
            fi
        done
    fi
    
    # PDF optimization
    echo ""
    echo "📄 PDF Processing Features:"
    echo "Install ghostscript for PDF optimization? (y/n)"
    read -r pdf_response
    if [[ "$pdf_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if command_exists gs; then
            echo -e "  ${GREEN}✓ ghostscript is already installed${NC}"
        else
            echo -e "  ${YELLOW}Installing ghostscript...${NC}"
            brew install ghostscript
        fi
    fi
    
    # Developer tools
    echo ""
    echo "👨‍💻 Developer Tools:"
    echo "Install bat for enhanced code display? (y/n)"
    read -r bat_response
    if [[ "$bat_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if command_exists bat; then
            echo -e "  ${GREEN}✓ bat is already installed${NC}"
        else
            echo -e "  ${YELLOW}Installing bat...${NC}"
            brew install bat
        fi
    fi
    
    echo "Install tldr for command descriptions? (y/n)"
    read -r tldr_response
    if [[ "$tldr_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if command_exists tldr; then
            echo -e "  ${GREEN}✓ tldr is already installed${NC}"
        else
            echo -e "  ${YELLOW}Installing tldr...${NC}"
            echo "Choose installation method:"
            echo "1) Via pip (Python)"
            echo "2) Via npm (Node.js)"
            echo "3) Via Homebrew"
            read -r tldr_method
            
            case $tldr_method in
                1)
                    $PYTHON_PATH -m pip install tldr
                    ;;
                2)
                    if command_exists npm; then
                        npm install -g tldr
                    else
                        echo -e "${RED}npm is not installed. Installing via pip instead...${NC}"
                        $PYTHON_PATH -m pip install tldr
                    fi
                    ;;
                3)
                    brew install tldr
                    ;;
                *)
                    echo "Invalid choice. Installing via pip..."
                    $PYTHON_PATH -m pip install tldr
                    ;;
            esac
        fi
    fi
fi

# Create necessary directories
echo ""
echo "📁 Creating necessary directories..."
if [ ! -d "reviews" ]; then
    mkdir reviews
    echo -e "  ${GREEN}✓ Created reviews/ directory${NC}"
else
    echo -e "  ${GREEN}✓ reviews/ directory already exists${NC}"
fi

# Make scripts executable
echo ""
echo "🔐 Setting executable permissions..."
if [ -f "show_review.sh" ]; then
    chmod +x show_review.sh
    echo -e "  ${GREEN}✓ Made show_review.sh executable${NC}"
fi

# Test the main application
echo ""
echo "🧪 Testing Raycast exam terminal UI..."
if $PYTHON_PATH -c "import curses, pandas, openpyxl" 2>/dev/null; then
    echo -e "${GREEN}✓ All core dependencies are properly installed${NC}"
else
    echo -e "${RED}✗ Some core dependencies are missing${NC}"
    exit 1
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "You can now run:"
echo "  python raycast_exam_terminal_ui.py   # Run the Raycast exam practice tool"
echo "  ./show_review.sh                     # Display code reviews (if available)"
echo ""
echo "Note: Please restart your terminal or run 'source ~/.zshrc' to use the python alias."
echo ""
echo "For more information, see README.md"