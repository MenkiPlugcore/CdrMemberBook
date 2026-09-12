from pathlib import Path
import re

# Fix generated admin usage string + status parser sentinel.
p = Path('src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java')
s = p.read_text()
s = re.sub(
    r'\s*sender\.sendMessage\(Colors\.legacy\("&f/" \+ label \+ " reports \[page\] \[open\|resolved\|all\] &8- &7list report\s*&f/" \+ label \+ " reports <search\|recent\|player> \.\.\. &8- &7QoL report lookup"\)\);',
    '\n        sender.sendMessage(Colors.legacy("&f/" + label + " reports [page] [open|resolved|all] &8- &7list report"));\n        sender.sendMessage(Colors.legacy("&f/" + label + " reports <search|recent|player> ... &8- &7QoL report lookup"));',
    s,
    flags=re.S,
)
s = s.replace('if (args.length >= 5 && filter == INVALID_STATUS) return;', 'if (args.length >= 5 && !isReportStatusToken(args[4])) return;')
s = s.replace('if (filter == INVALID_STATUS) return;', 'if (!isReportStatusToken(args[2])) return;')
start = s.find('    private static final ReportService.Status INVALID_STATUS')
end = s.find('    private int parsePositiveInt', start)
if start < 0 or end < 0:
    raise SystemExit('status parser block not found')
replacement = '''    private ReportService.Status parseReportStatus(CommandSender sender, String raw) {
        if (raw == null || raw.isBlank() || raw.equalsIgnoreCase("all")) return null;
        try { return ReportService.Status.valueOf(raw.toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ex) {
            sender.sendMessage(Colors.legacy("&cStatus harus open/resolved/all."));
            return null;
        }
    }

    private boolean isReportStatusToken(String raw) {
        if (raw == null || raw.isBlank()) return true;
        return raw.equalsIgnoreCase("all") || raw.equalsIgnoreCase("open") || raw.equalsIgnoreCase("resolved");
    }

'''
s = s[:start] + replacement + s[end:]
p.write_text(s)

# Normalize accidental escaped Java quotes only on generated target-count lines.
p = Path('src/main/java/id/cadera/memberbook/form/BedrockFormService.java')
lines = p.read_text().splitlines(True)
for i, line in enumerate(lines):
    if 'Total report target' in line or 'countByTarget(entry.targetUuid()' in line:
        lines[i] = line.replace('\\"', '"')
p.write_text(''.join(lines))

print('v1.9.5 post-patch cleanup applied')
