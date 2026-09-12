from pathlib import Path

p = Path('.github/scripts/upgrade_v195.py')
lines = p.read_text().splitlines(True)
idx = next((i for i, line in enumerate(lines) if "'bedrock detail count')" in line), None)
if idx is None:
    raise SystemExit('bedrock detail marker not found in upgrade script')
start = idx
while start >= 0 and not lines[start].startswith("s=replace_once(s,'''"):
    start -= 1
if start < 0:
    raise SystemExit('bedrock detail replace block start not found')
replacement = r'''target_old = ".append(\"Target: \").append(entry.targetName()).append('\\n')"
if target_old not in s:
    raise SystemExit('pattern not found: bedrock target line')
target_new = target_old + "\\n                .append(\\\"Total report target: \\\").append(plugin.reports().countByTarget(entry.targetUuid(), null))" + \
    "\\n                .append(\\\" (OPEN: \\\").append(plugin.reports().countByTarget(entry.targetUuid(), ReportService.Status.OPEN)).append(\\\")\\\\n\\\")"
s = s.replace(target_old, target_new, 1)
'''.splitlines(True)
lines[start:idx+1] = replacement
p.write_text(''.join(lines))
print('v1.9.5 upgrade marker patched')
