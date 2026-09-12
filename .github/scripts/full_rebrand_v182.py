from pathlib import Path
import re

root = Path('.')

# Scrub old server-specific branding from source/docs/resources.
for path in list(root.rglob('*.java')) + list(root.rglob('*.yml')) + list(root.glob('*.md')) + [root / 'pom.xml']:
    if not path.exists() or '.github' in path.parts:
        continue
    text = path.read_text()
    text = text.replace('MOONSIGN', 'CdrMemberBook')
    text = text.replace('MoonSign', 'CdrMemberBook')
    text = text.replace('moonsignmenu.', 'cdrmemberbook.')
    text = text.replace('moonsign:', 'cdrmemberbook:')
    path.write_text(text)

# Version bump.
pom = root / 'pom.xml'
s = pom.read_text().replace('<version>1.8.1</version>', '<version>1.8.2</version>', 1)
pom.write_text(s)

plugin = root / 'src/main/resources/plugin.yml'
s = plugin.read_text().replace("version: '1.8.1'", "version: '1.8.2'", 1)
# Remove the entire legacy permission alias section; official namespace is now only cdrmemberbook.*.
s = re.sub(r'\n  # Legacy permission aliases from pre-v1\.8\.1 builds\.[\s\S]*$', '\n', s)
plugin.write_text(s)

config = root / 'src/main/resources/config.yml'
s = config.read_text()
s = s.replace('# CdrMemberBook v1.8.1', '# CdrMemberBook v1.8.2', 1)
s = s.replace('config-version: 13', 'config-version: 14', 1)
config.write_text(s)

# Runtime migration for existing configs that still contain old server branding.
main = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = main.read_text()
s = s.replace('getLogger().info("CdrMemberBook v1.8.0 enabled.");',
              'getLogger().info("CdrMemberBook v1.8.2 enabled.");', 1)
old = '''        if (configVersion < 13) {
            getConfig().set("menu.hide-unavailable-buttons", true);
            getConfig().set("menu.auto-detect-command-dependencies", true);
            getConfig().set("integrations.report.enabled", true);
            getConfig().set("integrations.report.cooldown-seconds", 60L);
            getConfig().set("integrations.report.min-reason-length", 3);
            getConfig().set("integrations.report.max-reason-length", 200);
            getConfig().set("integrations.report.staff-permission", "cdrmemberbook.staff.report");
            getConfig().set("integrations.report.console-command", "");
            migrateSpecialButton("report", "report", "report", "report");
        }

        getConfig().set("config-version", 13);
        saveConfig();
    }
'''
new = '''        if (configVersion < 13) {
            getConfig().set("menu.hide-unavailable-buttons", true);
            getConfig().set("menu.auto-detect-command-dependencies", true);
            getConfig().set("integrations.report.enabled", true);
            getConfig().set("integrations.report.cooldown-seconds", 60L);
            getConfig().set("integrations.report.min-reason-length", 3);
            getConfig().set("integrations.report.max-reason-length", 200);
            getConfig().set("integrations.report.staff-permission", "cdrmemberbook.staff.report");
            getConfig().set("integrations.report.console-command", "");
            migrateSpecialButton("report", "report", "report", "report");
        }

        if (configVersion < 14) {
            migrateLegacyBranding();
        }

        getConfig().set("config-version", 14);
        saveConfig();
    }

    private void migrateLegacyBranding() {
        for (String key : new java.util.ArrayList<>(getConfig().getKeys(true))) {
            Object value = getConfig().get(key);
            if (value instanceof String text) {
                getConfig().set(key, rebrandLegacyText(text));
                continue;
            }
            if (value instanceof java.util.List<?> list) {
                java.util.List<Object> rewritten = new java.util.ArrayList<>(list.size());
                boolean changed = false;
                for (Object entry : list) {
                    if (entry instanceof String text) {
                        String updated = rebrandLegacyText(text);
                        rewritten.add(updated);
                        if (!updated.equals(text)) changed = true;
                    } else {
                        rewritten.add(entry);
                    }
                }
                if (changed) getConfig().set(key, rewritten);
            }
        }
    }

    private String rebrandLegacyText(String text) {
        return text
                .replace("MOON" + "SIGN", "CdrMemberBook")
                .replace("Moon" + "Sign", "CdrMemberBook")
                .replace("moon" + "signmenu.", "cdrmemberbook.")
                .replace("moon" + "sign:", "cdrmemberbook:");
    }
'''
if old not in s:
    raise SystemExit('config v13 migration block not found')
s = s.replace(old, new, 1)
main.write_text(s)

# README/changelog: make current public identity explicit, with no compatibility wording.
readme = root / 'README.md'
if readme.exists():
    s = readme.read_text().replace('v1.8.1', 'v1.8.2')
    s = re.sub(r'\n\n## Rebrand Cleanup v1\.8\.1[\s\S]*?(?=\n\n## |\Z)', '', s)
    s += '''\n\n## Full CdrMemberBook Branding v1.8.2\n\nCdrMemberBook is now fully server-agnostic. Public UI, default config, permission nodes, item/model namespace examples, tutorial, report system and documentation use only the **CdrMemberBook** identity. Official permissions use `cdrmemberbook.*`.\n'''
    readme.write_text(s)

changelog = root / 'CHANGELOG.md'
s = changelog.read_text() if changelog.exists() else '# Changelog\n'
entry = '''\n## 1.8.2 - Full CdrMemberBook Rebrand\n\n- Removed remaining server-specific branding and legacy permission aliases from the current plugin tree.\n- Official permission namespace is now only `cdrmemberbook.*`.\n- Added config migration v14 to rewrite old branding values in existing server configs.\n- Updated startup version and public documentation for the standalone plugin identity.\n'''
if '## 1.8.2 - Full CdrMemberBook Rebrand' not in s:
    s = s.replace('# Changelog\n', '# Changelog\n' + entry, 1)
s = s.replace('- Kept legacy permission aliases for backward compatibility.\n', '')
changelog.write_text(s)

# Verify current tracked product files no longer contain old branding literals.
for path in list(root.rglob('*.java')) + list(root.rglob('*.yml')) + list(root.glob('*.md')) + [root / 'pom.xml']:
    if not path.exists() or '.github' in path.parts:
        continue
    text = path.read_text()
    for forbidden in ('MOONSIGN', 'MoonSign', 'moonsignmenu.', 'moonsign:'):
        if forbidden in text:
            raise SystemExit(f'legacy branding remains in {path}: {forbidden}')

print('v1.8.2 full rebrand applied')
