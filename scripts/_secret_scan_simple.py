"""Simple secret leak scanner without pandas dependency."""
import re, sys
from pathlib import Path

SKIP_DIRS = {'__pycache__', '.git', '.venv', 'venv', 'node_modules'}
SKIP_SUFFIXES = {'.sqlite', '.db', '.pyc', '.png', '.jpg', '.jpeg', '.gif',
                 '.pdf', '.zip', '.gz', '.7z', '.exe', '.dll'}

SECRET_PATTERNS = [
    ('api_key_like', re.compile(r'sk-[a-z0-9]{2,}(?:-[a-z0-9]+)*-[A-Za-z0-9_-]{24,}', re.IGNORECASE)),
    ('bearer_token', re.compile(r'Authorization\s*[:=]\s*["\']?Bearer\s+([A-Za-z0-9_\-.]{24,})', re.IGNORECASE)),
    ('env_secret', re.compile(r'(OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|NOTION_TOKEN|DATABASE_URL)\s*[:=]\s*["\']?([A-Za-z0-9_\-./:]{24,})', re.IGNORECASE)),
    ('env_secret2', re.compile(r'(ETHERSCAN_API_KEY|TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)\s*[:=]\s*["\']?([A-Za-z0-9_\-:./]{16,})', re.IGNORECASE)),
    ('tg_bot_token', re.compile(r'\d{7,12}:[A-Za-z0-9_-]{30,}')),
    ('password', re.compile(r'(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\';\n]{16,})', re.IGNORECASE)),
    ('private_key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
]

ALLOW = ['OPENROUTER_API_KEY is missing', 'OPENROUTER_API_KEY`', '$env:OPENROUTER_API_KEY',
         '%OPENROUTER_API_KEY%', 'replace_with_', 'your_api_key', 'example_token',
         'ETHERSCAN_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
count = 0
for path in root.rglob('*'):
    if not path.is_file(): continue
    if set(path.parts) & SKIP_DIRS: continue
    if path.suffix.lower() in SKIP_SUFFIXES: continue
    try:
        if path.stat().st_size > 8*1024*1024: continue
        text = path.read_text(encoding='utf-8', errors='replace')
    except: continue
    for line in text.splitlines():
        if any(f in line for f in ALLOW): continue
        match = False
        for stype, pat in SECRET_PATTERNS:
            if pat.search(line):
                match = True
                break
        if match:
            count += 1
print(f'secret_leak_count: {count}')
