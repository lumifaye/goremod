import json, os, subprocess, tempfile
from pathlib import Path

script = Path(__file__).resolve().parents[2] / 'fork/ci-release.sh'
all_names = [
    'Realism64-Windows.zip', 'Realism64-Linux.zip',
    'Realism64-macOS-AppleSilicon.zip', 'Realism64-macOS-Intel.zip',
    'Realism64-VR-Windows.zip', 'Realism64-Android.apk', 'Realism64-VR-Quest.apk',
    'Realism64-WiiU.zip', 'SM64CoopDX-WiiU.zip', 'Realism64-WiiU.rpx', 'SM64CoopDX-WiiU.rpx',
]
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    gh = tmp / 'gh'
    gh.write_text('''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
notes = ''
if '--notes-file' in args:
    notes = open(args[args.index('--notes-file') + 1]).read()
with open(os.environ['MOCK_LOG'], 'a') as out:
    out.write(json.dumps({'args': args, 'notes': notes}) + '\\n')
if args[:2] == ['release', 'view']:
    sys.exit(0 if os.environ.get('MOCK_EXISTS') == '1' else 1)
sys.exit(0)
''')
    gh.chmod(0o755)
    log = tmp / 'calls.jsonl'
    env = os.environ.copy()
    env.update(PATH=str(tmp) + ':' + env.get('PATH',''), MOCK_LOG=str(log), GITHUB_RUN_NUMBER='23',
               GITHUB_SHA='1234567890abcdef', GITHUB_SERVER_URL='https://github.com', GITHUB_REPOSITORY='user/repo')
    def run(name, files, exists=False):
        folder = tmp / name; folder.mkdir()
        for file in files: (folder / file).write_text('artifact')
        if log.exists(): log.unlink()
        local = env.copy(); local['MOCK_EXISTS'] = '1' if exists else '0'
        result = subprocess.run(['bash', str(script), str(folder)], env=local, text=True, capture_output=True)
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls
    result, calls = run('all', all_names)
    assert result.returncode == 0, result.stderr
    create = next(c for c in calls if c['args'][:2] == ['release', 'create'])
    assert '--prerelease' in create['args'] and '--latest=false' in create['args']
    for name in all_names: assert str(tmp / 'all' / name) in create['args'], name
    assert 'console testing is limited' in create['notes'] and 'not in this build' not in create['notes']
    result, calls = run('wiiu-only', all_names[-4:])
    assert result.returncode == 0, result.stderr
    create = next(c for c in calls if c['args'][:2] == ['release', 'create'])
    assert '--prerelease' in create['args'] and '--latest=false' in create['args']
    assert 'not in this build:' in create['notes'] and 'console testing is limited' in create['notes']
    for name in all_names[-4:]: assert str(tmp / 'wiiu-only' / name) in create['args'], name
    result, calls = run('pc-only', [all_names[0]], exists=True)
    assert result.returncode == 0, result.stderr
    upload = next(c for c in calls if c['args'][:2] == ['release', 'upload'])
    edit = next(c for c in calls if c['args'][:2] == ['release', 'edit'])
    assert str(tmp / 'pc-only' / all_names[0]) in upload['args'] and '--clobber' in upload['args']
    assert '--prerelease' in edit['args'] and '--latest=false' in edit['args']
    assert 'console testing is limited' not in edit['notes']
    result, calls = run('empty', [])
    assert result.returncode != 0 and not calls, 'empty build must not create a release'
print('mock release tests passed')
