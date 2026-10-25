#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check local documentation links and the packaged setup download contract."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux.common import Error
from pbi_linux import onboarding

LINK = re.compile(r'!?\[[^\]]*\]\(\s*<?([^\s)>]+)>?(?:\s+"[^"\n]*")?\s*\)')


def visible_markdown(content):
    """Ignore examples inside fenced blocks, including embedded Markdown examples."""
    result, fence = [], None
    for line in content.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            result.append('')
        else:
            result.append(line if fence is None else '')
    return '\n'.join(result)


def headings(content):
    found, counts = set(), {}
    for line in visible_markdown(content).splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)(?:\s+#+)?$', line)
        if not match:
            continue
        text = re.sub(r'<[^>]*>', '', match[1]).lower()
        slug = re.sub(r'[^\w\-\s]', '', text).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(slug + ('-' + str(count) if count else ''))
    found.update(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', content))
    return found


def check(root=ROOT):
    errors = []
    pages = list(root.glob('*.md'))
    for directory in ('docs', 'tests/e2e', 'runtime/candidates'):
        pages.extend((root / directory).rglob('*.md'))
    for page in pages:
        for match in LINK.finditer(visible_markdown(page.read_text())):
            link = match[1]
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                continue
            target = (page.parent / unquote(parts.path)).resolve() if parts.path else page.resolve()
            label = str(page.relative_to(root)) + ': ' + link
            if not target.is_relative_to(root.resolve()) or not target.exists():
                errors.append(label + ' (missing local target)')
            elif parts.fragment and target.suffix == '.md':
                if unquote(parts.fragment) not in headings(target.read_text()):
                    errors.append(label + ' (missing heading)')
    try:
        manifest, _ = onboarding.release(root)
        if manifest.get('status') == 'ready':
            onboarding.validate_runtime_download(manifest.get('runtime'))
            onboarding.validate_download(manifest.get('powerbi'), microsoft=True)
        elif manifest.get('status') != 'pending' or not manifest.get('reason'):
            errors.append('packaging/setup.json: expected ready or pending with a reason')
    except (Error, ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append('packaging/setup.json: ' + str(exc))
    return errors


if __name__ == '__main__':
    errors = check()
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)
    print('Local documentation links, heading anchors and setup metadata passed.')
