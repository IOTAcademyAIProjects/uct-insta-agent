# Contributing to uct-insta-agent

Thank you for your interest in contributing! This guide explains how to add skills, fix bugs, and submit improvements.

---

## Ways to Contribute

- Add a new OpenClaw skill (most welcome!)
- Fix a bug in an existing pipeline
- Improve documentation
- Add support for a new free AI provider
- Improve the setup process

---

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/uct-insta-agent
cd uct-insta-agent
```
3. Create a branch:
```bash
git checkout -b feature/my-new-skill
```
4. Set up your environment following the Quick Start in README.md

---

## Rules — Read Before Contributing

### No paid APIs
Every AI provider, service, or tool must be completely free with no credit card required.
Do not add dependencies on: Anthropic Claude API (paid), OpenAI API (paid), or any service requiring payment.

### Free providers only
Approved free providers: NVIDIA NIM, Cerebras, Mistral, Pollinations AI, OpenRouter (free models only), Together AI (free tier), Cohere (free tier).

### No hardcoded credentials
Never commit API keys, tokens, or passwords. Use `.env` file and `os.getenv()`.

### Keep it simple
Skills should be simple Markdown files. Pipelines should be straightforward Python scripts. Avoid complex dependencies.

---

## Adding a New Skill

### Skill file format
```markdown
---
name: skill-name
description: One sentence describing what this skill does and when to trigger it.
---
# Skill Name

When user wants to do X, run:
~/your-script.sh ARGUMENT

Show the result to the user.
```

### Checklist for new skills
- [ ] SKILL.md has clear `name` and `description` in frontmatter
- [ ] Description tells the agent clearly WHEN to use this skill
- [ ] Shell script is in the repo root
- [ ] Pipeline Python file is in `pipelines/`
- [ ] No hardcoded API keys
- [ ] Tested locally on Lightning.ai
- [ ] Added to `setup.sh` skill recreation block
- [ ] Added to SKILLS.md documentation

---

## Adding a New AI Provider

Edit `pipelines/ai_router.py` and add to the PROVIDERS list:

```python
{
    "name": "YOUR_PROVIDER",
    "base_url": "https://api.yourprovider.com/v1",
    "api_key_env": "YOUR_PROVIDER_API_KEY",
    "model": "model-name",
},
```

Requirements:
- Must be OpenAI-compatible API (same request/response format)
- Must be completely free — no credit card
- Must work from Lightning.ai network
- Must work in India
- Add the env variable to `.env.example` with empty value

---

## Submitting a Pull Request

1. Test your changes thoroughly
2. Update SKILLS.md if you added a new skill
3. Update README.md if needed
4. Commit with a clear message:
```bash
git commit -m "feat: add instagram-reels skill for short video posting"
```
5. Push to your fork:
```bash
git push origin feature/my-new-skill
```
6. Open a Pull Request on GitHub with:
   - Clear title
   - Description of what you added/changed
   - Screenshot or output showing it works

---

## Commit Message Convention

```
feat: add new feature
fix: fix a bug
docs: update documentation
refactor: restructure code without changing behaviour
test: add or update tests
```

---

## Questions?

Open an issue on GitHub or contact the team at:
- **Abhishek Kumar Shukla** — Senior AI Developer
- **Organisation:** Uniconverge Technologies Pvt. Ltd.
- **Website:** www.uniconvergetech.in

---

*© 2026 Uniconverge Technologies Pvt. Ltd. — MIT License*
