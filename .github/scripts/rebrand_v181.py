from pathlib import Path

root = Path('.')

# Version bump
pom = root / 'pom.xml'
s = pom.read_text()
s = s.replace('<version>1.8.0</version>', '<version>1.8.1</version>', 1)
pom.write_text(s)

# Rebrand tracked text files. Keep legacy permission aliases added later.
for path in list(root.rglob('*.java')) + list(root.rglob('*.yml')) + list(root.glob('*.md')):
    if '.github' in path.parts:
        continue
    text = path.read_text()
    text = text.replace('MOONSIGN', 'CdrMemberBook')
    text = text.replace('MoonSign', 'CdrMemberBook')
    text = text.replace('moonsign:', 'cdrmemberbook:')
    text = text.replace('moonsignmenu.', 'cdrmemberbook.')
    path.write_text(text)

# Clean default UI wording after generic replacement.
config = root / 'src/main/resources/config.yml'
s = config.read_text()
s = s.replace('# CdrMemberBook v1.8.0', '# CdrMemberBook v1.8.1', 1)
s = s.replace("name: '&d&lCdrMemberBook &fMember Book'", "name: '&d&lCdrMemberBook'")
s = s.replace("- '&8Item menu pribadi CdrMemberBook.'", "- '&8Member Book dari CdrMemberBook.'")
s = s.replace("title: '&d&lCdrMemberBook &fMenu Member'", "title: '&d&lCdrMemberBook &fMenu'")
config.write_text(s)

# plugin.yml version + public description and compatibility aliases.
plugin = root / 'src/main/resources/plugin.yml'
s = plugin.read_text()
s = s.replace("version: '1.8.0'", "version: '1.8.1'", 1)
s = s.replace('description: Config-driven Bedrock/Java member menu with native TP, homes, pay and AxTrade flows for CdrMemberBook.',
              'description: Config-driven Bedrock/Java member menu with smart integrations, native reports, homes, pay and trade flows.')
legacy = '''\n  # Legacy permission aliases from pre-v1.8.1 builds.\n  # Keep these so existing LuckPerms assignments continue to grant the new CdrMemberBook nodes.\n  moonsignmenu.menu:\n    default: false\n    children:\n      cdrmemberbook.menu: true\n  moonsignmenu.tpa:\n    default: false\n    children:\n      cdrmemberbook.tpa: true\n  moonsignmenu.tpahere:\n    default: false\n    children:\n      cdrmemberbook.tpahere: true\n  moonsignmenu.tpaccept:\n    default: false\n    children:\n      cdrmemberbook.tpaccept: true\n  moonsignmenu.tpdeny:\n    default: false\n    children:\n      cdrmemberbook.tpdeny: true\n  moonsignmenu.tptoggle:\n    default: false\n    children:\n      cdrmemberbook.tptoggle: true\n  moonsignmenu.admin.reload:\n    default: false\n    children:\n      cdrmemberbook.admin.reload: true\n  moonsignmenu.admin.memberbook:\n    default: false\n    children:\n      cdrmemberbook.admin.memberbook: true\n  moonsignmenu.staff.report:\n    default: false\n    children:\n      cdrmemberbook.staff.report: true\n  moonsignmenu.bypass.cooldown:\n    default: false\n    children:\n      cdrmemberbook.bypass.cooldown: true\n  moonsignmenu.bypass.disabled:\n    default: false\n    children:\n      cdrmemberbook.bypass.disabled: true\n'''
if 'Legacy permission aliases from pre-v1.8.1 builds.' not in s:
    s = s.rstrip() + legacy
plugin.write_text(s + ('\n' if not s.endswith('\n') else ''))

# README version and rebrand note.
readme = root / 'README.md'
if readme.exists():
    s = readme.read_text()
    s = s.replace('v1.8.0', 'v1.8.1')
    if 'Rebrand Cleanup v1.8.1' not in s:
        s += '''\n\n## Rebrand Cleanup v1.8.1\n\nAll public-facing branding now uses **CdrMemberBook**. Default permission nodes use `cdrmemberbook.*`. Legacy `moonsignmenu.*` aliases remain only for backward compatibility with existing permission setups.\n'''
    readme.write_text(s)

# Changelog entry.
changelog = root / 'CHANGELOG.md'
s = changelog.read_text() if changelog.exists() else '# Changelog\n'
entry = '''\n## 1.8.1 - Rebrand Cleanup\n\n- Replaced public-facing server-specific branding with CdrMemberBook.\n- Changed default permission namespace to `cdrmemberbook.*`.\n- Kept legacy permission aliases for backward compatibility.\n- Updated default prefix, Member Book name/lore, tutorial title, menu title and item-model namespace example.\n'''
if '## 1.8.1 - Rebrand Cleanup' not in s:
    s = s.replace('# Changelog\n', '# Changelog\n' + entry, 1)
changelog.write_text(s)

# Verify no public uppercase brand remains outside compatibility history/aliases.
for path in list(root.rglob('*.java')) + list(root.rglob('*.yml')) + list(root.glob('*.md')):
    if '.github' in path.parts:
        continue
    text = path.read_text()
    if 'MOONSIGN' in text or 'MoonSign' in text:
        raise SystemExit(f'old public branding remains in {path}')

print('v1.8.1 rebrand applied')
