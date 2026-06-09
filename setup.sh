#!/bin/bash
echo "Setting up uct-insta-agent..."

# Install OpenClaw
npm install -g openclaw

# Install Node dependencies
npm install

# Install Python dependencies
pip install composio-core python-dotenv anthropic requests --break-system-packages

# Create Instagram post shell script
cat > ~/post-to-instagram.sh << 'EOF'
#!/bin/bash
cd /teamspace/studios/this_studio/uct-insta-agent
/home/zeus/miniconda3/envs/cloudspace/bin/python3 pipelines/post-with-caption.py "$1" "$2" "$3"
EOF
chmod +x ~/post-to-instagram.sh

# Create OpenClaw Instagram skill
mkdir -p ~/.openclaw/workspace/skills/instagram-post
cat > ~/.openclaw/workspace/skills/instagram-post/SKILL.md << 'EOF'
---
name: instagram-post
description: Post images to Instagram with AI-generated captions. Use when user wants to post to Instagram.
---
# Instagram Post

When user wants to post to Instagram, run this command:

```bash
~/post-to-instagram.sh "IMAGE_URL" "DESCRIPTION" "TONE"
```

Default TONE: casual
Default DESCRIPTION: a beautiful image
EOF

echo "Done! Now:"
echo "1. Fill in your .env file"
echo "2. Run: openclaw gateway run"
