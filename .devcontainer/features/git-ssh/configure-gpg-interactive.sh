#!/bin/bash
# Interactive GPG Configuration Script for OC Fetcher devcontainer
# This script configures GPG signing when a user opens a shell
# It detects if running in an agent environment and behaves accordingly

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to get detailed key information
get_key_details() {
    local key_id="$1"
    local key_info=$(gpg --list-secret-keys --keyid-format=long --with-colons 2>/dev/null | grep "^sec:" | grep "$key_id")

    if [[ -z "$key_info" ]]; then
        echo "Unknown key"
        return
    fi

    # Extract information from colon-separated format
    # Format: sec:e:3072:1:5490110527D629D3:1673436791:1736508791::u:::sc:::+:::23::0:
    local creation_date=$(echo "$key_info" | cut -d: -f6)
    local expiry_date=$(echo "$key_info" | cut -d: -f7)

    # Get the user ID (email/name) for this key
    local uid_info=$(gpg --list-secret-keys --keyid-format=long --with-colons 2>/dev/null | grep -A5 "^sec:.*$key_id" | grep "^uid:" | head -1)
    local email_name=$(echo "$uid_info" | cut -d: -f10)

    # Format dates
    local creation_formatted=""
    local expiry_formatted=""

    if [[ -n "$creation_date" && "$creation_date" != "" ]]; then
        creation_formatted=$(date -d "@$creation_date" "+%Y-%m-%d" 2>/dev/null || echo "Unknown")
    fi

    if [[ -n "$expiry_date" && "$expiry_date" != "" ]]; then
        expiry_formatted=$(date -d "@$expiry_date" "+%Y-%m-%d" 2>/dev/null || echo "Unknown")
    else
        expiry_formatted="Never"
    fi

    # Check if key is expired
    local status=""
    if [[ "$expiry_date" != "" && "$expiry_date" -lt $(date +%s) ]]; then
        status="${RED}(EXPIRED)${NC} "
    fi

    echo "${status}${email_name} (Created: $creation_formatted, Expires: $expiry_formatted)"
}

# Check if this is an agent session or non-interactive
if [[ -n "${CURSOR_AGENT:-}" ]] || [[ ! -t 0 ]]; then
    # Agent session or non-interactive - be completely silent if configured
    if git config --global user.signingkey >/dev/null 2>&1; then
        SIGNING_KEY=$(git config --global user.signingkey)
        # Check if the key is expired
        if gpg --list-secret-keys --keyid-format=long 2>/dev/null | grep -q "$SIGNING_KEY"; then
            # Get expiry date for the key
            EXPIRY_DATE=$(gpg --list-secret-keys --keyid-format=long --with-colons 2>/dev/null | grep "^sec:" | grep "$SIGNING_KEY" | cut -d: -f7)
            if [[ -n "$EXPIRY_DATE" && "$EXPIRY_DATE" != "" && "$EXPIRY_DATE" -lt $(date +%s) ]]; then
                echo -e "${RED}⚠️  GPG key $SIGNING_KEY has expired. Run 'configure-gpg' to set up a new key.${NC}"
            fi
            # If not expired, be completely silent
        fi
    else
        echo -e "${YELLOW}ℹ GPG signing not configured. Run 'configure-gpg' to set it up.${NC}"
    fi
    return 0 2>/dev/null || true
fi

# Check if GPG is already configured
if git config --global user.signingkey >/dev/null 2>&1; then
    SIGNING_KEY=$(git config --global user.signingkey)

    # Check if the key exists and is not expired
    if gpg --list-secret-keys --keyid-format=long 2>/dev/null | grep -q "$SIGNING_KEY"; then
        # Get expiry date for the key
        EXPIRY_DATE=$(gpg --list-secret-keys --keyid-format=long --with-colons 2>/dev/null | grep "^sec:" | grep "$SIGNING_KEY" | cut -d: -f7)
        if [[ -n "$EXPIRY_DATE" && "$EXPIRY_DATE" != "" && "$EXPIRY_DATE" -lt $(date +%s) ]]; then
            echo -e "${RED}⚠️  GPG key $SIGNING_KEY has expired.${NC}"
            echo -e "${BLUE}🔐 Please configure a new GPG key...${NC}"
        else
            # Key is valid and not expired - be silent
            return 0 2>/dev/null || true
        fi
    else
        echo -e "${YELLOW}⚠️  Configured GPG key $SIGNING_KEY not found.${NC}"
        echo -e "${BLUE}🔐 Please configure a new GPG key...${NC}"
    fi
fi

echo -e "${BLUE}🔐 Configuring GPG signing...${NC}"

# Check if GPG is available
if ! command -v gpg >/dev/null 2>&1; then
    echo -e "${RED}❌ GPG not found. Please install GPG first.${NC}"
    return 1 2>/dev/null || true
fi

# Check if GPG keys are available
if ! gpg --list-secret-keys --keyid-format=long >/dev/null 2>&1; then
    echo -e "${YELLOW}ℹ No GPG keys found. GPG signing will be disabled.${NC}"
    echo -e "${YELLOW}   To enable GPG signing, ensure your GPG keys are mounted from the host.${NC}"
    return 0 2>/dev/null || true
fi

# Get available secret keys
SECRET_KEYS=$(gpg --list-secret-keys --keyid-format=long 2>/dev/null | grep -E "^sec" || true)

if [[ -z "$SECRET_KEYS" ]]; then
    echo -e "${YELLOW}ℹ No secret keys found. GPG signing will be disabled.${NC}"
    return 0 2>/dev/null || true
fi

# Count available keys
KEY_COUNT=$(echo "$SECRET_KEYS" | wc -l)
echo -e "${BLUE}📋 Found $KEY_COUNT GPG key(s)${NC}"

# Display available keys with detailed information
echo -e "${BLUE}Available keys:${NC}"
gpg --list-secret-keys --keyid-format=long 2>/dev/null | grep -E "^sec" | while read -r line; do
    KEY_ID=$(echo "$line" | sed -n 's/.*\/\([A-F0-9]\{16\}\).*/\1/p')
    KEY_DETAILS=$(get_key_details "$KEY_ID")
    echo -e "  ${GREEN}•${NC} ${CYAN}$KEY_ID${NC} - $KEY_DETAILS"
done

# Check for GPG key ID in .gpg_key file
SELECTED_KEY=""
if [[ -f ".gpg_key" ]]; then
    USER_KEY=$(cat .gpg_key | tr -d '\n\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ -n "$USER_KEY" ]]; then
        # Verify the specified key exists
        if gpg --list-secret-keys --keyid-format=long 2>/dev/null | grep -q "$USER_KEY"; then
            echo -e "${BLUE}🔑 Using GPG key from .gpg_key file: $USER_KEY${NC}"
            SELECTED_KEY="$USER_KEY"
        else
            echo -e "${YELLOW}⚠️  GPG key $USER_KEY from .gpg_key file not found${NC}"
        fi
    fi
fi

# If no key from .gpg_key file or key not found, prompt user
if [[ -z "$SELECTED_KEY" ]]; then
    echo -e "${BLUE}📋 No GPG key specified in .gpg_key file${NC}"
    echo -e "${YELLOW}💡 To find your GPG key ID, run: gpg --list-secret-keys --keyid-format=long${NC}"
    echo -e "${YELLOW}   Look for a line like: sec   rsa4096/1234567890ABCDEF 2023-01-01 [SC]${NC}"
    echo -e "${YELLOW}   The key ID is the 16-character hex string after the slash${NC}"
    echo ""

    # Show available keys with detailed information
    echo -e "${BLUE}Available GPG keys:${NC}"
    gpg --list-secret-keys --keyid-format=long 2>/dev/null | grep -E "^sec" | while read -r line; do
        KEY_ID=$(echo "$line" | sed -n 's/.*\/\([A-F0-9]\{16\}\).*/\1/p')
        KEY_DETAILS=$(get_key_details "$KEY_ID")
        echo -e "  ${GREEN}•${NC} ${CYAN}$KEY_ID${NC} - $KEY_DETAILS"
    done
    echo ""

    # Prompt user for key selection
    while true; do
        echo -e "${BLUE}🔑 Please enter your GPG key ID (16-character hex string) or press Enter to use the first available key:${NC}"
        read -r USER_INPUT

        # If user pressed Enter, use first available key
        if [[ -z "$USER_INPUT" ]]; then
            SELECTED_KEY=$(echo "$SECRET_KEYS" | head -1 | sed -n 's/.*\/\([A-F0-9]\{16\}\).*/\1/p')
            if [[ -n "$SELECTED_KEY" ]]; then
                echo -e "${BLUE}🔑 Using first available key: $SELECTED_KEY${NC}"
                break
            else
                echo -e "${RED}❌ No GPG keys available${NC}"
                return 1 2>/dev/null || true
            fi
        fi

        # Validate key format (16 hex characters)
        if [[ "$USER_INPUT" =~ ^[A-F0-9]{16}$ ]]; then
            # Check if key exists
            if gpg --list-secret-keys --keyid-format=long 2>/dev/null | grep -q "$USER_INPUT"; then
                SELECTED_KEY="$USER_INPUT"
                echo -e "${BLUE}🔑 Using selected key: $SELECTED_KEY${NC}"

                # Ask if user wants to save this key to .gpg_key file
                echo -e "${BLUE}💾 Would you like to save this key to .gpg_key file for future use? (y/n):${NC}"
                read -r SAVE_CHOICE
                if [[ "$SAVE_CHOICE" =~ ^[Yy]$ ]]; then
                    echo "$SELECTED_KEY" > .gpg_key
                    echo -e "${GREEN}✅ GPG key saved to .gpg_key file${NC}"
                fi
                break
            else
                echo -e "${RED}❌ GPG key $USER_INPUT not found. Please check the key ID and try again.${NC}"
            fi
        else
            echo -e "${RED}❌ Invalid key format. Please enter a 16-character hex string (e.g., 1234567890ABCDEF).${NC}"
        fi
    done
fi

if [[ -n "$SELECTED_KEY" ]]; then

    # Configure Git GPG signing
    git config --global user.signingkey "$SELECTED_KEY" 2>/dev/null || {
        echo -e "${RED}❌ Failed to set signing key${NC}"
        return 1 2>/dev/null || true
    }

    git config --global commit.gpgsign true 2>/dev/null || {
        echo -e "${RED}❌ Failed to enable commit signing${NC}"
        return 1 2>/dev/null || true
    }

    git config --global tag.gpgsign true 2>/dev/null || {
        echo -e "${RED}❌ Failed to enable tag signing${NC}"
        return 1 2>/dev/null || true
    }

    # Test GPG signing
    if echo "test" | gpg --clearsign >/dev/null 2>&1; then
        echo -e "${GREEN}✅ GPG signing configured successfully!${NC}"
        echo -e "${GREEN}   • Commit signing: enabled${NC}"
        echo -e "${GREEN}   • Tag signing: enabled${NC}"
        echo -e "${GREEN}   • Signing key: $SELECTED_KEY${NC}"
    else
        echo -e "${YELLOW}⚠️  GPG signing configured but test failed${NC}"
        echo -e "${YELLOW}   You may need to enter your passphrase for the first commit${NC}"
    fi
else
    echo -e "${RED}❌ No valid GPG key found${NC}"
    return 1 2>/dev/null || true
fi
