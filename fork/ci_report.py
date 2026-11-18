"""Puts a text file on a commit's page as a "check", where it can be read without downloading a log:

    python3 fork/ci_report.py <name> <file> [<file>...]

Used by .github/workflows/build-fork.yml for the list of compiler errors. One check holds 65,000 letters; a
longer file becomes several ("<name> 1/3", ...). Needs GITHUB_TOKEN (with "checks: write"), GITHUB_REPOSITORY
and GITHUB_SHA, which a workflow has. Never fails the step it runs in.
"""
import json
import os
import sys
import urllib.request

LIMIT = 60000


def post(name, text):
    body = {
        'name': name,
        'head_sha': os.environ['GITHUB_SHA'],
        'status': 'completed',
        'conclusion': 'neutral',
        'output': {'title': name, 'summary': '%d letters' % len(text), 'text': '```\n' + text + '\n```'},
    }
    request = urllib.request.Request(
        'https://api.github.com/repos/%s/check-runs' % os.environ['GITHUB_REPOSITORY'],
        data=json.dumps(body).encode(),
        headers={
            'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
            'User-Agent': 'gore-hardmode-ci',
        },
    )
    urllib.request.urlopen(request).read()


def main():
    name = sys.argv[1]
    text = ''
    for path in sys.argv[2:]:
        try:
            with open(path, errors='replace') as f:
                text += f.read()
        except OSError as error:
            text += '(%s: %s)\n' % (path, error)
    text = text.replace('```', "'''") or '(empty)'
    parts = [text[i:i + LIMIT] for i in range(0, len(text), LIMIT)][:8]
    for number, part in enumerate(parts, 1):
        title = name if len(parts) == 1 else '%s %d/%d' % (name, number, len(parts))
        try:
            post(title, part)
        except Exception as error:
            print('ci_report: %s: %s' % (title, error))


if __name__ == '__main__':
    main()
