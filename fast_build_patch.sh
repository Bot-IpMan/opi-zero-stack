#!/bin/bash
set -e

# Define paths
MAKEFILE="./Makefile"
REQ_FILE="./requirements.txt"
BACKUP_EXT=".bak.$(date +%s)"

echo ">>> Starting build optimization patch..."

# 1. Patch Makefile
if [ -f "$MAKEFILE" ]; then
    echo "Found Makefile at $MAKEFILE"
    cp "$MAKEFILE" "$MAKEFILE$BACKUP_EXT"
    echo "Backup created at $MAKEFILE$BACKUP_EXT"

    # Strategy: Replace simple 'pip install -r requirements.txt' with the optimized version
    # We use sed to look for the line and replace it.
    # We also add the pip upgrade command before it if possible, but for simplicity, we'll chain them.
    
    # Optimization flags
    PIP_OPTS="--prefer-binary --only-binary=:all:"
    
    # Check if we can find the standard pip install command
    if grep -q "pip install -r requirements.txt" "$MAKEFILE"; then
        echo "Patching 'pip install -r requirements.txt'..."
        # We replace the line with a block that updates pip/wheel first, then installs with optimizations
        # Note: We use a temporary file to avoid complex sed escaping if possible, but sed is faster for in-place.
        # using | as delimiter
        sed -i "s|pip install -r requirements.txt|python -m pip install --upgrade pip setuptools wheel \&\& python -m pip install $PIP_OPTS -r requirements.txt|g" "$MAKEFILE"
        echo "Makefile patched successfully."
    else
        echo "WARNING: Could not find exact match for 'pip install -r requirements.txt'. appending optimization target..."
        # Append a new target explicit for fast build if the user wants to run it manually
        echo "" >> "$MAKEFILE"
        echo "fast-install-deps:" >> "$MAKEFILE"
        echo -e "\tpython -m pip install --upgrade pip setuptools wheel" >> "$MAKEFILE"
        echo -e "\tpython -m pip install $PIP_OPTS -r requirements.txt" >> "$MAKEFILE"
        echo -e "\tpython -m pip install --prefer-binary opencv-python-headless || true" >> "$MAKEFILE"
        echo "Added 'fast-install-deps' target to Makefile."
    fi
else
    echo "ERROR: Makefile not found at $MAKEFILE"
fi

# 2. Patch requirements.txt (Optional but recommended)
if [ -f "$REQ_FILE" ]; then
    echo "Found requirements.txt at $REQ_FILE"
    cp "$REQ_FILE" "$REQ_FILE$BACKUP_EXT"
    
    # Check if opencv is present without version pin
    if grep -qE "^opencv-python-headless$" "$REQ_FILE"; then
        echo "Pinning opencv-python-headless to 4.9.0.80 for manylinux support..."
        sed -i 's/^opencv-python-headless$/opencv-python-headless==4.9.0.80/g' "$REQ_FILE"
    elif grep -q "opencv-python-headless" "$REQ_FILE"; then
        echo "opencv-python-headless is already present (possibly pinned), skipping modification."
    else
        echo "opencv-python-headless not found in requirements.txt. Skipping."
    fi
fi

# 3. Dockerfile check (Tip only)
if [ -f "Dockerfile" ]; then
    echo "Found Dockerfile."
    echo "SUGGESTION: Add 'RUN apt-get update && apt-get install -y libopencv-dev' before pip install to speed up build further."
fi

echo ">>> Patch applied."
echo "Now run 'make opi-build' (or 'make fast-install-deps' if the patch appended a new target)."
