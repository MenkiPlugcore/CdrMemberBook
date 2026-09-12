from pathlib import Path

script = Path('.github/scripts/upgrade_v151.py')
source = script.read_text()
old = 's, count = pattern.subn(replacement, s, count=1)'
new = 's, count = pattern.subn(lambda _: replacement, s, count=1)'
if old not in source:
    raise SystemExit('expected subn pattern not found')
source = source.replace(old, new, 1)
exec(compile(source, str(script), 'exec'))
