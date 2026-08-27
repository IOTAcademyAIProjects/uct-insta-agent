#!/bin/bash
set -e
echo "============================================================"
echo " Setting up ClawAgent v3.0 (Social Media AI Operating System)"
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Install OpenClaw globally (if npm is present)
if command -v npm &> /dev/null; then
  echo "Installing OpenClaw..."
  npm install -g openclaw || true
  npm install || true
fi

# 2. Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --break-system-packages || pip install -r requirements.txt

# 3. Ensure executable permissions on shell scripts
chmod +x "$SCRIPT_DIR"/*.sh

# 4. Copy wrapper shell scripts to home directory for OpenClaw access
echo "Wiring wrapper scripts to home directory..."
for script in dm-manager.sh generate-image.sh post-analytics.sh \
              post-approve.sh post-carousel.sh post-preview.sh \
              post-reject.sh post-story.sh post-to-instagram.sh scheduler.sh; do
  if [ -f "$SCRIPT_DIR/$script" ]; then
    cp "$SCRIPT_DIR/$script" ~/"$script"
    chmod +x ~/"$script"
  fi
done

# 5. Initialize SQLite Database with all 13 tables
echo "Initializing SQLite database with v3.0 schemas..."
python3 db/setup_db.py

# 6. Verify Model Router configuration
echo "Verifying Model Stack..."
python3 cli.py ai-status

echo ""
echo "============================================================"
echo " Setup Complete! Next steps:"
echo " 1. Configure your API keys in .env (see .env.example)"
echo " 2. Review config/models.yaml to adjust provider routing"
echo " 3. Run: python3 cli.py ai-status to verify provider credentials"
echo " 4. Start posting: python3 cli.py preview <image_url>"
echo "============================================================"