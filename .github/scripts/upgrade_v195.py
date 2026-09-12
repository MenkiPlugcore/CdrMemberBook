from pathlib import Path

root = Path('.')

def read(path):
    return (root / path).read_text()

def write(path, content):
    (root / path).write_text(content)

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)

def replace_between(text, start, end, new, label):
    a = text.find(start)
    if a < 0:
        raise SystemExit(f'start not found: {label}')
    b = text.find(end, a)
    if b < 0:
        raise SystemExit(f'end not found: {label}')
    return text[:a] + new + text[b:]

# Versions
p='pom.xml'; s=read(p); s=replace_once(s,'<version>1.9.4</version>','<version>1.9.5</version>','pom version'); write(p,s)
p='src/main/resources/plugin.yml'; s=read(p); s=replace_once(s,"version: '1.9.4'","version: '1.9.5'",'plugin version'); write(p,s)

# ReportService v1.9.5
write('src/main/java/id/cadera/memberbook/report/ReportService.java', r'''package id.cadera.memberbook.report;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Colors;
import org.bukkit.Bukkit;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;

import java.io.File;
import java.io.IOException;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

public final class ReportService {
    private final CdrMemberBookPlugin plugin;
    private final File file;
    private YamlConfiguration data;
    private final Map<UUID, Long> cooldownUntil = new HashMap<>();

    public ReportService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.file = new File(plugin.getDataFolder(), "reports.yml");
        this.data = YamlConfiguration.loadConfiguration(file);
    }

    public boolean enabled() { return plugin.getConfig().getBoolean("integrations.report.enabled", true); }

    public SubmitResult submit(Player reporter, Player target, String rawReason) {
        if (!enabled()) return new SubmitResult(false, 0, 0, "disabled");
        if (reporter.getUniqueId().equals(target.getUniqueId())) return new SubmitResult(false, 0, 0, "self");
        String reason = sanitizeText(rawReason);
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) return new SubmitResult(false, 0, 0, "short");
        if (reason.length() > max) reason = reason.substring(0, max).trim();

        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(reporter.getUniqueId(), 0L);
        if (until > now) return new SubmitResult(false, 0, Math.max(1L, (until - now + 999L) / 1000L), "cooldown");

        DuplicateMatch duplicate = findDuplicate(reporter.getUniqueId(), target.getUniqueId(), now);
        if (duplicate != null) {
            return new SubmitResult(false, duplicate.id(), duplicate.waitSeconds(), "duplicate");
        }

        int id = Math.max(1, data.getInt("next-id", 1));
        String base = "reports." + id + ".";
        String createdAt = Instant.now().toString();
        data.set(base + "status", Status.OPEN.name());
        data.set(base + "created-at", createdAt);
        data.set(base + "reporter.name", reporter.getName());
        data.set(base + "reporter.uuid", reporter.getUniqueId().toString());
        data.set(base + "target.name", target.getName());
        data.set(base + "target.uuid", target.getUniqueId().toString());
        data.set(base + "reason", reason);
        data.set(base + "world", reporter.getWorld().getName());
        data.set(base + "location.x", reporter.getLocation().getBlockX());
        data.set(base + "location.y", reporter.getLocation().getBlockY());
        data.set(base + "location.z", reporter.getLocation().getBlockZ());
        data.set(base + "resolved-at", null);
        data.set(base + "resolved-by", null);
        data.set(base + "notes", new ArrayList<>());
        data.set(base + "audit", new ArrayList<>());
        appendAuditInMemory(id, "CREATE", reporter.getName(), "Report dibuat untuk " + target.getName());
        data.set("next-id", id + 1);
        if (!save()) {
            reloadFromDisk();
            return new SubmitResult(false, 0, 0, "storage");
        }

        long cooldown = Math.max(0L, plugin.getConfig().getLong("integrations.report.cooldown-seconds", 60L));
        if (cooldown > 0L) cooldownUntil.put(reporter.getUniqueId(), now + cooldown * 1000L);
        notifyStaff(id, reporter, target, reason);
        runConsoleHook(id, reporter, target, reason);
        plugin.getLogger().info("Report #" + id + ": " + reporter.getName() + " -> " + target.getName() + " | " + reason);
        return new SubmitResult(true, id, 0, "ok");
    }

    public ReportEntry get(int id) {
        if (id <= 0 || !data.isConfigurationSection("reports." + id)) return null;
        return readEntry(id);
    }

    public List<ReportEntry> list(Status filter) {
        ConfigurationSection section = data.getConfigurationSection("reports");
        if (section == null) return List.of();
        List<ReportEntry> result = new ArrayList<>();
        for (String raw : section.getKeys(false)) {
            try {
                int id = Integer.parseInt(raw);
                ReportEntry entry = readEntry(id);
                if (entry != null && (filter == null || entry.status() == filter)) result.add(entry);
            } catch (NumberFormatException ignored) { }
        }
        result.sort(Comparator.comparingInt(ReportEntry::id).reversed());
        return List.copyOf(result);
    }

    public List<ReportEntry> search(String query, SearchField field, Status filter) {
        String needle = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        if (needle.isBlank()) return list(filter);
        SearchField effective = field == null ? SearchField.ANY : field;
        return list(filter).stream().filter(entry -> switch (effective) {
            case REPORTER -> contains(entry.reporterName(), needle) || contains(entry.reporterUuid(), needle);
            case TARGET -> contains(entry.targetName(), needle) || contains(entry.targetUuid(), needle);
            case ANY -> contains(entry.reporterName(), needle) || contains(entry.reporterUuid(), needle)
                    || contains(entry.targetName(), needle) || contains(entry.targetUuid(), needle);
        }).toList();
    }

    public List<ReportEntry> recent(int limit, Status filter) {
        int safe = Math.max(1, Math.min(100, limit));
        List<ReportEntry> entries = list(filter);
        return List.copyOf(entries.subList(0, Math.min(safe, entries.size())));
    }

    public int count(Status filter) { return list(filter).size(); }

    public int countByTarget(String query, Status filter) {
        return search(query, SearchField.TARGET, filter).size();
    }

    public int countByReporter(String query, Status filter) {
        return search(query, SearchField.REPORTER, filter).size();
    }

    public boolean resolve(int id, String staff) {
        ReportEntry entry = get(id);
        if (entry == null) return false;
        String base = "reports." + id + ".";
        data.set(base + "status", Status.RESOLVED.name());
        data.set(base + "resolved-at", Instant.now().toString());
        data.set(base + "resolved-by", safeStaff(staff));
        appendAuditInMemory(id, "RESOLVE", safeStaff(staff), "Status OPEN -> RESOLVED");
        if (save()) return true;
        reloadFromDisk();
        return false;
    }

    public boolean reopen(int id, String staff) {
        if (get(id) == null) return false;
        String base = "reports." + id + ".";
        data.set(base + "status", Status.OPEN.name());
        data.set(base + "resolved-at", null);
        data.set(base + "resolved-by", null);
        appendAuditInMemory(id, "REOPEN", safeStaff(staff), "Status RESOLVED -> OPEN");
        if (!save()) { reloadFromDisk(); return false; }
        plugin.getLogger().info("Report #" + id + " reopened by " + safeStaff(staff));
        return true;
    }

    public boolean addNote(int id, String staff, String rawNote) {
        if (get(id) == null) return false;
        String note = sanitizeText(rawNote);
        int maxLength = Math.max(10, plugin.getConfig().getInt("integrations.report.audit.max-note-length", 240));
        if (note.isBlank()) return false;
        if (note.length() > maxLength) note = note.substring(0, maxLength).trim();
        String path = "reports." + id + ".notes";
        List<Map<?, ?>> current = data.getMapList(path);
        List<Map<String, Object>> notes = new ArrayList<>();
        for (Map<?, ?> raw : current) notes.add(copyMap(raw));
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("at", Instant.now().toString());
        map.put("staff", safeStaff(staff));
        map.put("text", note);
        notes.add(map);
        trimFront(notes, Math.max(1, plugin.getConfig().getInt("integrations.report.audit.max-notes", 20)));
        data.set(path, notes);
        appendAuditInMemory(id, "NOTE", safeStaff(staff), note);
        if (save()) return true;
        reloadFromDisk();
        return false;
    }

    public boolean delete(int id) {
        ReportEntry entry = get(id);
        if (entry == null) return false;
        plugin.getLogger().info("Report #" + id + " deleted | " + entry.reporterName() + " -> " + entry.targetName());
        data.set("reports." + id, null);
        if (save()) return true;
        reloadFromDisk();
        return false;
    }

    public Status parseStatus(String raw) {
        if (raw == null || raw.isBlank() || raw.equalsIgnoreCase("all")) return null;
        try { return Status.valueOf(raw.trim().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { return null; }
    }

    public SearchField parseSearchField(String raw) {
        if (raw == null || raw.isBlank() || raw.equalsIgnoreCase("any") || raw.equalsIgnoreCase("player")) return SearchField.ANY;
        if (raw.equalsIgnoreCase("reporter")) return SearchField.REPORTER;
        if (raw.equalsIgnoreCase("target")) return SearchField.TARGET;
        return null;
    }

    private DuplicateMatch findDuplicate(UUID reporter, UUID target, long nowMillis) {
        long windowSeconds = Math.max(0L, plugin.getConfig().getLong("integrations.report.duplicate-window-seconds", 300L));
        if (windowSeconds <= 0L) return null;
        long windowMillis = windowSeconds * 1000L;
        for (ReportEntry entry : list(null)) {
            if (!entry.reporterUuid().equalsIgnoreCase(reporter.toString()) || !entry.targetUuid().equalsIgnoreCase(target.toString())) continue;
            long created = instantMillis(entry.createdAt());
            if (created <= 0L) continue;
            long age = nowMillis - created;
            if (age >= 0L && age < windowMillis) {
                long wait = Math.max(1L, (windowMillis - age + 999L) / 1000L);
                return new DuplicateMatch(entry.id(), wait);
            }
        }
        return null;
    }

    private ReportEntry readEntry(int id) {
        String base = "reports." + id + ".";
        if (!data.isConfigurationSection("reports." + id)) return null;
        Status status;
        try { status = Status.valueOf(data.getString(base + "status", "OPEN").toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { status = Status.OPEN; }
        List<StaffNote> notes = new ArrayList<>();
        for (Map<?, ?> raw : data.getMapList(base + "notes")) {
            notes.add(new StaffNote(string(raw.get("at")), string(raw.get("staff")), string(raw.get("text"))));
        }
        List<AuditEntry> audit = new ArrayList<>();
        for (Map<?, ?> raw : data.getMapList(base + "audit")) {
            audit.add(new AuditEntry(string(raw.get("at")), string(raw.get("action")), string(raw.get("actor")), string(raw.get("detail"))));
        }
        return new ReportEntry(id, status, data.getString(base + "created-at", "unknown"),
                data.getString(base + "reporter.name", "unknown"), data.getString(base + "reporter.uuid", ""),
                data.getString(base + "target.name", "unknown"), data.getString(base + "target.uuid", ""),
                data.getString(base + "reason", ""), data.getString(base + "world", "unknown"),
                data.getInt(base + "location.x"), data.getInt(base + "location.y"), data.getInt(base + "location.z"),
                data.getString(base + "resolved-at", ""), data.getString(base + "resolved-by", ""),
                List.copyOf(notes), List.copyOf(audit));
    }

    private void appendAuditInMemory(int id, String action, String actor, String detail) {
        String path = "reports." + id + ".audit";
        List<Map<?, ?>> current = data.getMapList(path);
        List<Map<String, Object>> audit = new ArrayList<>();
        for (Map<?, ?> raw : current) audit.add(copyMap(raw));
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("at", Instant.now().toString());
        map.put("action", action);
        map.put("actor", safeStaff(actor));
        map.put("detail", sanitizeText(detail));
        audit.add(map);
        trimFront(audit, Math.max(1, plugin.getConfig().getInt("integrations.report.audit.max-history", 50)));
        data.set(path, audit);
    }

    private Map<String, Object> copyMap(Map<?, ?> raw) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : raw.entrySet()) if (entry.getKey() != null) out.put(entry.getKey().toString(), entry.getValue());
        return out;
    }

    private <T> void trimFront(List<T> list, int max) {
        while (list.size() > max) list.remove(0);
    }

    private boolean contains(String value, String needleLower) {
        return value != null && value.toLowerCase(Locale.ROOT).contains(needleLower);
    }

    private long instantMillis(String raw) {
        try { return Instant.parse(raw).toEpochMilli(); }
        catch (DateTimeParseException | NullPointerException ignored) { return -1L; }
    }

    private String string(Object value) { return value == null ? "" : value.toString(); }

    private String sanitizeText(String raw) {
        String input = raw == null ? "" : raw;
        if (!plugin.getConfig().getBoolean("integrations.report.sanitize-control-characters", true)) return input.trim();
        StringBuilder out = new StringBuilder(input.length());
        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);
            if (c == '\n' || c == '\r' || c == '\t') out.append(' ');
            else if (!Character.isISOControl(c)) out.append(c);
        }
        return out.toString().replaceAll("\\s+", " ").trim();
    }

    private String safeStaff(String staff) { return staff == null || staff.isBlank() ? "Console" : staff; }

    private void notifyStaff(int id, Player reporter, Player target, String reason) {
        String permission = plugin.getConfig().getString("integrations.report.staff-permission", "cdrmemberbook.staff.report");
        String message = "&8[&cREPORT #" + id + "&8] &f" + reporter.getName() + " &7melaporkan &f" + target.getName() + "&7: &f" + reason;
        for (Player online : Bukkit.getOnlinePlayers()) if (permission == null || permission.isBlank() || online.hasPermission(permission)) online.sendMessage(Colors.legacy(message));
    }

    private void runConsoleHook(int id, Player reporter, Player target, String reason) {
        String template = plugin.getConfig().getString("integrations.report.console-command", "");
        if (template == null || template.isBlank()) return;
        String command = template.replace("%id%", Integer.toString(id)).replace("%reporter%", reporter.getName())
                .replace("%target%", target.getName()).replace("%reason%", reason);
        if (command.startsWith("/")) command = command.substring(1);
        try { Bukkit.dispatchCommand(Bukkit.getConsoleSender(), command); }
        catch (Throwable throwable) { plugin.getLogger().warning("Report console hook failed: " + throwable.getMessage()); }
    }

    private boolean save() {
        try { data.save(file); return true; }
        catch (IOException exception) {
            plugin.getLogger().severe("Could not save reports.yml: " + exception.getMessage());
            return false;
        }
    }

    private void reloadFromDisk() { data = YamlConfiguration.loadConfiguration(file); }

    public enum Status { OPEN, RESOLVED }
    public enum SearchField { REPORTER, TARGET, ANY }
    public record SubmitResult(boolean success, int id, long waitSeconds, String reasonCode) { }
    public record StaffNote(String at, String staff, String text) { }
    public record AuditEntry(String at, String action, String actor, String detail) { }
    public record ReportEntry(int id, Status status, String createdAt, String reporterName, String reporterUuid,
                              String targetName, String targetUuid, String reason, String world,
                              int x, int y, int z, String resolvedAt, String resolvedBy,
                              List<StaffNote> notes, List<AuditEntry> audit) { }
    private record DuplicateMatch(int id, long waitSeconds) { }
}
''')

# Admin command: replace report list/report handlers with QoL commands.
p='src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'; s=read(p)
new_reports = r'''    private void handleReports(CommandSender sender, String[] args) {
        if (args.length >= 2 && args[1].equalsIgnoreCase("search")) {
            if (args.length < 4) {
                sender.sendMessage(Colors.legacy("&f/cdrmemberbook reports search <reporter|target|any> <player> [open|resolved|all] [page]"));
                return;
            }
            ReportService.SearchField field = plugin.reports().parseSearchField(args[2]);
            if (field == null) { sender.sendMessage(Colors.legacy("&cField harus reporter/target/any.")); return; }
            ReportService.Status filter = parseReportStatus(sender, args.length >= 5 ? args[4] : "all");
            if (args.length >= 5 && filter == INVALID_STATUS) return;
            int page = parsePositiveInt(args.length >= 6 ? args[5] : "1", 1);
            sendReportPage(sender, plugin.reports().search(args[3], field, filter), page,
                    "search " + field + "=" + args[3]);
            return;
        }
        if (args.length >= 2 && args[1].equalsIgnoreCase("recent")) {
            int limit = parsePositiveInt(args.length >= 3 ? args[2] : Integer.toString(plugin.getConfig().getInt("integrations.report.recent-limit", 10)), 10);
            sendReportPage(sender, plugin.reports().recent(limit, null), 1, "recent");
            return;
        }
        if (args.length >= 2 && args[1].equalsIgnoreCase("player")) {
            if (args.length < 3) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook reports player <name>")); return; }
            String q = args[2];
            sender.sendMessage(Colors.legacy("&dReport Stats &8- &f" + q));
            sender.sendMessage(Colors.legacy("&7Sebagai reporter: &f" + plugin.reports().countByReporter(q, null)
                    + " &8| &7Sebagai target: &f" + plugin.reports().countByTarget(q, null)
                    + " &8(open=&f" + plugin.reports().countByTarget(q, ReportService.Status.OPEN) + "&8)"));
            sendReportPage(sender, plugin.reports().search(q, ReportService.SearchField.ANY, null), 1, "player " + q);
            return;
        }
        int page = 1;
        if (args.length >= 2) try { page = Math.max(1, Integer.parseInt(args[1])); } catch (NumberFormatException ignored) { }
        ReportService.Status filter = null;
        if (args.length >= 3) {
            filter = parseReportStatus(sender, args[2]);
            if (filter == INVALID_STATUS) return;
        }
        sendReportPage(sender, plugin.reports().list(filter), page, filter == null ? "all" : filter.name());
    }

    private static final ReportService.Status INVALID_STATUS = ReportService.Status.valueOf("OPEN");

    private ReportService.Status parseReportStatus(CommandSender sender, String raw) {
        if (raw == null || raw.isBlank() || raw.equalsIgnoreCase("all")) return null;
        try { return ReportService.Status.valueOf(raw.toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ex) {
            sender.sendMessage(Colors.legacy("&cStatus harus open/resolved/all."));
            return INVALID_STATUS;
        }
    }

    private int parsePositiveInt(String raw, int fallback) {
        try { return Math.max(1, Integer.parseInt(raw)); }
        catch (NumberFormatException ignored) { return Math.max(1, fallback); }
    }

    private void sendReportPage(CommandSender sender, List<ReportService.ReportEntry> entries, int requestedPage, String label) {
        int size = Math.max(1, plugin.getConfig().getInt("integrations.report.admin-page-size", 8));
        int pages = Math.max(1, (entries.size() + size - 1) / size);
        int page = Math.max(1, Math.min(requestedPage, pages));
        int start = (page - 1) * size;
        int end = Math.min(entries.size(), start + size);
        sender.sendMessage(Colors.legacy("&dCdrMemberBook Reports &8- &f" + page + "/" + pages + " &8| &7" + label
                + " &8| &7total=&f" + entries.size() + " &8| &7open=&f" + plugin.reports().count(ReportService.Status.OPEN)));
        if (entries.isEmpty()) { sender.sendMessage(Colors.legacy("&7Tidak ada report.")); return; }
        for (int i = start; i < end; i++) {
            ReportService.ReportEntry e = entries.get(i);
            sender.sendMessage(Colors.legacy((e.status() == ReportService.Status.OPEN ? "&c" : "&a") + "#" + e.id()
                    + " &f" + e.reporterName() + " &8-> &f" + e.targetName() + " &8| &7" + shorten(e.reason(), 48)
                    + (e.notes().isEmpty() ? "" : " &8| &e" + e.notes().size() + " note")));
        }
    }

'''
s=replace_between(s,'    private void handleReports(CommandSender sender, String[] args) {','    private void handleReport(CommandSender sender, String[] args) {',new_reports,'admin reports method')
new_report = r'''    private void handleReport(CommandSender sender, String[] args) {
        if (args.length < 3) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook report <view|resolve|reopen|delete|note|audit> <id> [text]")); return; }
        int id;
        try { id = Integer.parseInt(args[2]); } catch (NumberFormatException ex) { sender.sendMessage(Colors.legacy("&cID report tidak valid.")); return; }
        if (id <= 0) { sender.sendMessage(Colors.legacy("&cID report harus lebih dari 0.")); return; }
        String action = args[1].toLowerCase(Locale.ROOT);
        ReportService.ReportEntry e = plugin.reports().get(id);
        if (e == null) { sender.sendMessage(Colors.legacy("&cReport #" + id + " tidak ditemukan.")); return; }
        String staff = sender.getName();
        switch (action) {
            case "view" -> {
                sender.sendMessage(Colors.legacy("&dReport #" + e.id() + " &8- &f" + e.status()));
                sender.sendMessage(Colors.legacy("&7Reporter: &f" + e.reporterName() + " &8(" + e.reporterUuid() + ")"));
                sender.sendMessage(Colors.legacy("&7Target: &f" + e.targetName() + " &8(" + e.targetUuid() + ") &8| &7Total target reports: &f" + plugin.reports().countByTarget(e.targetUuid(), null)));
                sender.sendMessage(Colors.legacy("&7Alasan: &f" + e.reason()));
                sender.sendMessage(Colors.legacy("&7Waktu: &f" + e.createdAt() + " &8| &7Lokasi: &f" + e.world() + " " + e.x() + "," + e.y() + "," + e.z()));
                if (e.status() == ReportService.Status.RESOLVED) sender.sendMessage(Colors.legacy("&7Resolved: &f" + e.resolvedBy() + " &8@ &f" + e.resolvedAt()));
                if (!e.notes().isEmpty()) {
                    ReportService.StaffNote note = e.notes().get(e.notes().size() - 1);
                    sender.sendMessage(Colors.legacy("&7Latest note: &e" + note.staff() + "&8: &f" + note.text()));
                }
                sender.sendMessage(Colors.legacy("&7Audit entries: &f" + e.audit().size() + " &8| &7Notes: &f" + e.notes().size()));
            }
            case "resolve" -> sender.sendMessage(Colors.legacy(plugin.reports().resolve(id, staff)
                    ? "&aReport #" + id + " ditandai RESOLVED." : "&cGagal menyimpan perubahan report #" + id + "."));
            case "reopen" -> sender.sendMessage(Colors.legacy(plugin.reports().reopen(id, staff)
                    ? "&eReport #" + id + " dibuka kembali." : "&cGagal menyimpan perubahan report #" + id + "."));
            case "delete" -> sender.sendMessage(Colors.legacy(plugin.reports().delete(id)
                    ? "&aReport #" + id + " dihapus." : "&cGagal menghapus report #" + id + "."));
            case "note" -> {
                if (args.length < 4) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook report note " + id + " <catatan staff>")); return; }
                String note = String.join(" ", java.util.Arrays.copyOfRange(args, 3, args.length));
                sender.sendMessage(Colors.legacy(plugin.reports().addNote(id, staff, note)
                        ? "&aCatatan staff ditambahkan ke report #" + id + "." : "&cGagal menambah catatan report #" + id + "."));
            }
            case "audit" -> {
                sender.sendMessage(Colors.legacy("&dAudit Report #" + id + " &8- &7" + e.audit().size() + " event"));
                int start = Math.max(0, e.audit().size() - 10);
                for (int i = start; i < e.audit().size(); i++) {
                    ReportService.AuditEntry audit = e.audit().get(i);
                    sender.sendMessage(Colors.legacy("&8- &f" + audit.action() + " &7by &f" + audit.actor() + " &8| &7" + shorten(audit.detail(), 72) + " &8@ " + audit.at()));
                }
            }
            default -> sender.sendMessage(Colors.legacy("&cAction report harus view/resolve/reopen/delete/note/audit."));
        }
    }

'''
s=replace_between(s,'    private void handleReport(CommandSender sender, String[] args) {','    private void sendHealth(CommandSender sender) {',new_report,'admin report method')
s=s.replace('&dCdrMemberBook Health &8- &fv1.9.2','&dCdrMemberBook Health &8- &fv1.9.5')
s=s.replace('&dCdrMemberBook &fv1.9.2 &8- &7Admin Tools','&dCdrMemberBook &fv1.9.5 &8- &7Admin Tools')
s=s.replace('&f/" + label + " reports [page] [open|resolved|all] &8- &7list report','&f/" + label + " reports [page] [open|resolved|all] &8- &7list report\n&f/" + label + " reports <search|recent|player> ... &8- &7QoL report lookup')
s=s.replace('&f/" + label + " report <view|resolve|reopen|delete> <id>','&f/" + label + " report <view|resolve|reopen|delete|note|audit> <id> [text]')
s=s.replace('List.of("view","resolve","reopen","delete")','List.of("view","resolve","reopen","delete","note","audit")')
write(p,s)

# Main plugin config migration and startup version.
p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
s=s.replace('CdrMemberBook v1.9.4 enabled.','CdrMemberBook v1.9.5 enabled.')
old='''        if (configVersion < 21) {
            getConfig().set("java-menu.decorations.enabled", true);
            getConfig().set("java-menu.decorations.filler-material", "BLACK_STAINED_GLASS_PANE");
            getConfig().set("java-menu.decorations.accent-material", "MAGENTA_STAINED_GLASS_PANE");
            getConfig().set("java-menu.decorations.click-hint", true);
            String platform = getConfig().getString("menu.main.buttons.report-center.conditions.platform", "");
            if (platform != null && platform.equalsIgnoreCase("BEDROCK")) {
                getConfig().set("menu.main.buttons.report-center.conditions.platform", "ANY");
            }
        }

        getConfig().set("config-version", 21);'''
new='''        if (configVersion < 21) {
            getConfig().set("java-menu.decorations.enabled", true);
            getConfig().set("java-menu.decorations.filler-material", "BLACK_STAINED_GLASS_PANE");
            getConfig().set("java-menu.decorations.accent-material", "MAGENTA_STAINED_GLASS_PANE");
            getConfig().set("java-menu.decorations.click-hint", true);
            String platform = getConfig().getString("menu.main.buttons.report-center.conditions.platform", "");
            if (platform != null && platform.equalsIgnoreCase("BEDROCK")) {
                getConfig().set("menu.main.buttons.report-center.conditions.platform", "ANY");
            }
        }

        if (configVersion < 22) {
            getConfig().set("integrations.report.duplicate-window-seconds", 300L);
            getConfig().set("integrations.report.recent-limit", 10);
            getConfig().set("integrations.report.audit.max-history", 50);
            getConfig().set("integrations.report.audit.max-notes", 20);
            getConfig().set("integrations.report.audit.max-note-length", 240);
            getConfig().set("integrations.report.center.show-recent", true);
            getConfig().set("integrations.report.center.show-search", true);
            getConfig().set("integrations.report.center.detail-note-limit", 3);
            getConfig().set("integrations.report.center.detail-audit-limit", 5);
        }

        getConfig().set("config-version", 22);'''
s=replace_once(s,old,new,'config migration 22')
write(p,s)

# Config additions/messages/header.
p='src/main/resources/config.yml'; s=read(p)
s=s.replace('# CdrMemberBook v1.9.4\nconfig-version: 21','# CdrMemberBook v1.9.5\nconfig-version: 22')
s=replace_once(s,"    cooldown-seconds: 60\n    min-reason-length: 3","    cooldown-seconds: 60\n    # Reporter yang sama tidak bisa spam target yang sama dalam window ini. 0 = disable.\n    duplicate-window-seconds: 300\n    # Jumlah default untuk daftar Recent Reports.\n    recent-limit: 10\n    min-reason-length: 3",'report duplicate config')
s=replace_once(s,"    console-command: ''\n    # Native Bedrock staff Report Center.","    console-command: ''\n    audit:\n      max-history: 50\n      max-notes: 20\n      max-note-length: 240\n    # Native Java + Bedrock staff Report Center.",'audit config')
s=replace_once(s,"      allow-delete: true\n","      allow-delete: true\n      show-recent: true\n      show-search: true\n      detail-note-limit: 3\n      detail-audit-limit: 5\n",'center QoL config')
s=replace_once(s,"  report-cooldown: '&eTunggu &f%seconds%s &esebelum membuat laporan lagi.'\n","  report-cooldown: '&eTunggu &f%seconds%s &esebelum membuat laporan lagi.'\n  report-duplicate: '&eKamu baru saja melaporkan player ini. Report sebelumnya: &f#%id%&e. Coba lagi dalam &f%seconds%s&e.'\n  report-note-added: '&aCatatan staff ditambahkan ke report &f#%id%&a.'\n",'report messages')
write(p,s)

# Bedrock: duplicate message + Report Center search/recent + notes/audit display/add-note.
p='src/main/java/id/cadera/memberbook/form/BedrockFormService.java'; s=read(p)
s=replace_once(s,'''                    } else if ("cooldown".equals(result.reasonCode())) {
                        plugin.message(player, "report-cooldown", "%seconds%", Long.toString(result.waitSeconds()));
                        showConfiguredMenu(player, returnMenuId);
                    } else if ("self".equals(result.reasonCode())) {''','''                    } else if ("cooldown".equals(result.reasonCode())) {
                        plugin.message(player, "report-cooldown", "%seconds%", Long.toString(result.waitSeconds()));
                        showConfiguredMenu(player, returnMenuId);
                    } else if ("duplicate".equals(result.reasonCode())) {
                        plugin.message(player, "report-duplicate", "%id%", Integer.toString(result.id()),
                                "%seconds%", Long.toString(result.waitSeconds()));
                        showConfiguredMenu(player, returnMenuId);
                    } else if ("self".equals(result.reasonCode())) {''','bedrock duplicate message')
new_center = r'''    private void showReportCenter(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        int open = plugin.reports().count(ReportService.Status.OPEN);
        int resolved = plugin.reports().count(ReportService.Status.RESOLVED);
        int all = open + resolved;
        boolean showRecent = plugin.getConfig().getBoolean("integrations.report.center.show-recent", true);
        boolean showSearch = plugin.getConfig().getBoolean("integrations.report.center.show-search", true);

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Report Center")
                .content("Kelola laporan langsung dari Member Book.\nOPEN: " + open
                        + " | RESOLVED: " + resolved + " | TOTAL: " + all);
        addButton(builder, "Open Reports (" + open + ")", "report", "textures/items/book_writable");
        addButton(builder, "Resolved Reports (" + resolved + ")", "report", "textures/items/book_written");
        addButton(builder, "Semua Reports (" + all + ")", "report", "textures/items/book_normal");
        if (showRecent) addButton(builder, "Recent Reports", "refresh", "textures/items/clock_item");
        if (showSearch) addButton(builder, "Cari Reporter / Target", "player", "textures/items/name_tag");
        addButton(builder, "Refresh", "refresh", "textures/items/compass_item");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int recentIndex = showRecent ? 3 : -1;
        int searchIndex = showSearch ? (showRecent ? 4 : 3) : -1;
        int refreshIndex = 3 + (showRecent ? 1 : 0) + (showSearch ? 1 : 0);
        int backIndex = refreshIndex + 1;
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!ensureReportStaff(player, returnMenuId)) return;
            int selected = response.clickedButtonId();
            if (selected == 0) showReportList(player, returnMenuId, ReportService.Status.OPEN, 1);
            else if (selected == 1) showReportList(player, returnMenuId, ReportService.Status.RESOLVED, 1);
            else if (selected == 2) showReportList(player, returnMenuId, null, 1);
            else if (selected == recentIndex) showRecentReportList(player, returnMenuId);
            else if (selected == searchIndex) showReportSearchType(player, returnMenuId);
            else if (selected == refreshIndex) showReportCenter(player, returnMenuId);
            else if (selected == backIndex) showConfiguredMenu(player, returnMenuId);
        })).build());
    }

    private void showRecentReportList(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        int limit = Math.max(1, Math.min(20, plugin.getConfig().getInt("integrations.report.recent-limit", 10)));
        showReportCustomList(player, returnMenuId, "Recent Reports", plugin.reports().recent(limit, null));
    }

    private void showReportSearchType(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        SimpleForm.Builder builder = SimpleForm.builder().title("Cari Report").content("Cari berdasarkan nama/UUID reporter atau target.");
        addButton(builder, "Cari Reporter", "player", "textures/items/name_tag");
        addButton(builder, "Cari Target", "player", "textures/items/name_tag");
        addButton(builder, "Cari Keduanya", "player", "textures/items/compass_item");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!ensureReportStaff(player, returnMenuId)) return;
            switch (response.clickedButtonId()) {
                case 0 -> showReportSearchInput(player, returnMenuId, ReportService.SearchField.REPORTER);
                case 1 -> showReportSearchInput(player, returnMenuId, ReportService.SearchField.TARGET);
                case 2 -> showReportSearchInput(player, returnMenuId, ReportService.SearchField.ANY);
                case 3 -> showReportCenter(player, returnMenuId);
                default -> { }
            }
        })).build());
    }

    private void showReportSearchInput(Player player, String returnMenuId, ReportService.SearchField field) {
        CustomForm form = CustomForm.builder()
                .title("Cari Report • " + field.name())
                .input("Nama / UUID player", "contoh: Caderaaa", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showReportSearchType(player, returnMenuId)))
                .validResultHandler(response -> sync(() -> {
                    if (!ensureReportStaff(player, returnMenuId)) return;
                    String query = response.asInput(0);
                    if (query == null || query.trim().isEmpty()) { showReportSearchType(player, returnMenuId); return; }
                    showReportCustomList(player, returnMenuId, "Search " + field.name(), plugin.reports().search(query.trim(), field, null));
                })).build();
        send(player, form);
    }

    private void showReportCustomList(Player player, String returnMenuId, String title, List<ReportService.ReportEntry> entries) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        SimpleForm.Builder builder = SimpleForm.builder().title(title)
                .content(entries.isEmpty() ? "Tidak ada report yang cocok." : "Ditemukan " + entries.size() + " report.");
        int max = Math.min(20, entries.size());
        for (int i = 0; i < max; i++) {
            ReportService.ReportEntry entry = entries.get(i);
            addButton(builder, "#" + entry.id() + " • " + entry.targetName() + "\n" + entry.status() + " • oleh " + entry.reporterName(),
                    "report", entry.status() == ReportService.Status.OPEN ? "textures/items/book_writable" : "textures/items/book_written");
        }
        addButton(builder, "Kembali ke Report Center", "back", "textures/items/arrow");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!ensureReportStaff(player, returnMenuId)) return;
            int selected = response.clickedButtonId();
            if (selected >= 0 && selected < max) showReportDetail(player, returnMenuId, null, 1, entries.get(selected).id());
            else if (selected == max) showReportCenter(player, returnMenuId);
        })).build());
    }

'''
s=replace_between(s,'    private void showReportCenter(Player player, String returnMenuId) {','    private void showReportList(Player player, String returnMenuId, ReportService.Status filter, int requestedPage) {',new_center,'bedrock report center')
# Detail content: add counts, latest notes/audit and Add Note button.
s=replace_once(s,'''.append("Target: ").append(entry.targetName()).append('\n')
                .append("Waktu: ").append(entry.createdAt()).append('\n')''','''.append("Target: ").append(entry.targetName()).append('\n')
                .append("Total report target: ").append(plugin.reports().countByTarget(entry.targetUuid(), null))
                .append(" (OPEN: ").append(plugin.reports().countByTarget(entry.targetUuid(), ReportService.Status.OPEN)).append(")\n")
                .append("Waktu: ").append(entry.createdAt()).append('\n')''','bedrock detail count')
s=replace_once(s,'''        if (entry.status() == ReportService.Status.RESOLVED) {
            content.append("\\n\\nResolved by: ").append(entry.resolvedBy())
                    .append("\\nResolved at: ").append(entry.resolvedAt());
        }

        boolean allowDelete''','''        if (entry.status() == ReportService.Status.RESOLVED) {
            content.append("\\n\\nResolved by: ").append(entry.resolvedBy())
                    .append("\\nResolved at: ").append(entry.resolvedAt());
        }
        int noteLimit = Math.max(1, plugin.getConfig().getInt("integrations.report.center.detail-note-limit", 3));
        if (!entry.notes().isEmpty()) {
            content.append("\\n\\nStaff Notes:");
            int startNote = Math.max(0, entry.notes().size() - noteLimit);
            for (int i = startNote; i < entry.notes().size(); i++) {
                ReportService.StaffNote note = entry.notes().get(i);
                content.append("\\n- ").append(note.staff()).append(": ").append(note.text());
            }
        }
        int auditLimit = Math.max(1, plugin.getConfig().getInt("integrations.report.center.detail-audit-limit", 5));
        if (!entry.audit().isEmpty()) {
            content.append("\\n\\nAudit:");
            int startAudit = Math.max(0, entry.audit().size() - auditLimit);
            for (int i = startAudit; i < entry.audit().size(); i++) {
                ReportService.AuditEntry audit = entry.audit().get(i);
                content.append("\\n- ").append(audit.action()).append(" by ").append(audit.actor());
            }
        }

        boolean allowDelete''','bedrock notes audit')
s=replace_once(s,'''        if (entry.status() == ReportService.Status.OPEN) {
            addButton(builder, "Resolve Report", "confirm", "textures/items/emerald");
        } else {
            addButton(builder, "Reopen Report", "refresh", "textures/items/compass_item");
        }
        if (allowDelete) addButton(builder, "Hapus Report", "delete", "textures/items/barrier");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int deleteIndex = allowDelete ? 1 : -1;
        int backIndex = allowDelete ? 2 : 1;''','''        if (entry.status() == ReportService.Status.OPEN) {
            addButton(builder, "Resolve Report", "confirm", "textures/items/emerald");
        } else {
            addButton(builder, "Reopen Report", "refresh", "textures/items/compass_item");
        }
        addButton(builder, "Tambah Catatan Staff", "report", "textures/items/paper");
        if (allowDelete) addButton(builder, "Hapus Report", "delete", "textures/items/barrier");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int noteIndex = 1;
        int deleteIndex = allowDelete ? 2 : -1;
        int backIndex = allowDelete ? 3 : 2;''','bedrock note button')
s=replace_once(s,'''            if (selected == deleteIndex) {
                showReportActionConfirm(player, returnMenuId, filter, page, reportId, "delete");
                return;
            }
            if (selected == backIndex) showReportList(player, returnMenuId, filter, page);''','''            if (selected == noteIndex) {
                showReportNoteInput(player, returnMenuId, filter, page, reportId);
                return;
            }
            if (selected == deleteIndex) {
                showReportActionConfirm(player, returnMenuId, filter, page, reportId, "delete");
                return;
            }
            if (selected == backIndex) showReportList(player, returnMenuId, filter, page);''','bedrock note click')
insert_note = r'''    private void showReportNoteInput(Player player, String returnMenuId, ReportService.Status filter, int page, int reportId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        CustomForm form = CustomForm.builder()
                .title("Catatan Report #" + reportId)
                .input("Catatan staff", "contoh: Sudah cek log, menunggu bukti tambahan", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showReportDetail(player, returnMenuId, filter, page, reportId)))
                .validResultHandler(response -> sync(() -> {
                    if (!ensureReportStaff(player, returnMenuId)) return;
                    String note = response.asInput(0);
                    if (note == null || note.trim().isEmpty()) { showReportDetail(player, returnMenuId, filter, page, reportId); return; }
                    if (plugin.reports().addNote(reportId, player.getName(), note)) {
                        plugin.message(player, "report-note-added", "%id%", Integer.toString(reportId));
                    } else plugin.message(player, "report-action-failed");
                    showReportDetail(player, returnMenuId, filter, page, reportId);
                })).build();
        send(player, form);
    }

'''
s=replace_once(s,'    private void showReportActionConfirm(Player player, String returnMenuId, ReportService.Status filter,',insert_note+'    private void showReportActionConfirm(Player player, String returnMenuId, ReportService.Status filter,','bedrock insert note method')
write(p,s)

# Java Report Center: recent/search-help and richer detail audit/notes.
p='src/main/java/id/cadera/memberbook/gui/JavaMenuService.java'; s=read(p)
s=s.replace('    private static final String REPORT_REFRESH = "__report_refresh";','    private static final String REPORT_REFRESH = "__report_refresh";\n    private static final String REPORT_RECENT = "__report_recent";\n    private static final String REPORT_SEARCH_HELP = "__report_search_help";')
new_java_center = r'''    private void showReportCenter(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        int open = plugin.reports().count(ReportService.Status.OPEN);
        int resolved = plugin.reports().count(ReportService.Status.RESOLVED);
        int all = open + resolved;

        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CENTER, null, returnMenuId, 0, 36,
                "§8CdrMemberBook §7• §cReports");
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));
        inventory.setItem(4, item(Material.WRITTEN_BOOK, "&c&lReport Center", List.of(
                "&7OPEN: &f" + open,
                "&7RESOLVED: &f" + resolved,
                "&7TOTAL: &f" + all
        )));
        inventory.setItem(10, navigationItem(Material.WRITABLE_BOOK, "&cOpen Reports &7(" + open + ")", REPORT_OPEN, "&7Lihat laporan yang masih aktif."));
        inventory.setItem(12, navigationItem(Material.WRITTEN_BOOK, "&aResolved Reports &7(" + resolved + ")", REPORT_RESOLVED, "&7Lihat laporan yang sudah selesai."));
        inventory.setItem(14, navigationItem(Material.BOOK, "&fSemua Reports &7(" + all + ")", REPORT_ALL, "&7Lihat seluruh laporan."));
        inventory.setItem(16, navigationItem(Material.COMPASS, "&bRefresh", REPORT_REFRESH, "&7Perbarui jumlah laporan."));
        if (plugin.getConfig().getBoolean("integrations.report.center.show-recent", true)) {
            inventory.setItem(20, navigationItem(Material.CLOCK, "&eRecent Reports", REPORT_RECENT, "&7Lihat report terbaru."));
        }
        if (plugin.getConfig().getBoolean("integrations.report.center.show-search", true)) {
            inventory.setItem(22, navigationItem(Material.NAME_TAG, "&bCari Report", REPORT_SEARCH_HELP,
                    "&7Gunakan command search:\n&f/cdrmemberbook reports search <reporter|target|any> <nama>"));
        }
        inventory.setItem(31, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Member Menu."));
        player.openInventory(inventory);
    }

    private void showRecentReportList(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        int limit = Math.max(1, Math.min(PAGE_SIZE, plugin.getConfig().getInt("integrations.report.recent-limit", 10)));
        List<ReportService.ReportEntry> entries = plugin.reports().recent(limit, null);
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_LIST, null, returnMenuId, 0,
                "ALL", 0, 54, "§8Reports §7• §eRecent");
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, 0, 1, "Recent Reports");
        int slotIndex = 0;
        for (ReportService.ReportEntry entry : entries) {
            Material material = entry.status() == ReportService.Status.OPEN ? Material.WRITABLE_BOOK : Material.WRITTEN_BOOK;
            ItemStack item = item(material, (entry.status() == ReportService.Status.OPEN ? "&c" : "&a") + "Report #" + entry.id() + " &8• &f" + entry.targetName(), List.of(
                    "&7Reporter: &f" + entry.reporterName(), "&7Status: &f" + entry.status(), "&7Alasan: &f" + shorten(entry.reason(), 42), "", "&8» &fKlik untuk detail."));
            ItemMeta meta = item.getItemMeta();
            meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, REPORT_PREFIX + entry.id());
            item.setItemMeta(meta);
            inventory.setItem(CONTENT_SLOTS[slotIndex++], item);
        }
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eReport Center", NAV_BACK, "&7Kembali ke Report Center."));
        player.openInventory(inventory);
    }

'''
s=replace_between(s,'    private void showReportCenter(Player player, String returnMenuId) {','    private void handleReportCenterClick(Player player, MenuHolder holder, ItemStack clicked) {',new_java_center,'java report center')
s=replace_once(s,'''        else if (REPORT_ALL.equals(action)) showReportList(player, holder.menuId(), null, 0);
        else if (REPORT_REFRESH.equals(action)) showReportCenter(player, holder.menuId());
        else if (NAV_BACK.equals(action)) showConfiguredMenu(player, holder.menuId(), 0);''','''        else if (REPORT_ALL.equals(action)) showReportList(player, holder.menuId(), null, 0);
        else if (REPORT_RECENT.equals(action)) showRecentReportList(player, holder.menuId());
        else if (REPORT_SEARCH_HELP.equals(action)) {
            player.closeInventory();
            player.sendMessage(Colors.legacy("&bCari report: &f/cdrmemberbook reports search <reporter|target|any> <nama> [open|resolved|all]"));
        }
        else if (REPORT_REFRESH.equals(action)) showReportCenter(player, holder.menuId());
        else if (NAV_BACK.equals(action)) showConfiguredMenu(player, holder.menuId(), 0);''','java center handler')
s=replace_once(s,'''        details.add("&7Target: &f" + entry.targetName());
        details.add("&7Waktu: &f" + entry.createdAt());''','''        details.add("&7Target: &f" + entry.targetName());
        details.add("&7Total report target: &f" + plugin.reports().countByTarget(entry.targetUuid(), null)
                + " &8(OPEN: &f" + plugin.reports().countByTarget(entry.targetUuid(), ReportService.Status.OPEN) + "&8)");
        details.add("&7Waktu: &f" + entry.createdAt());''','java target count')
s=replace_once(s,'''        if (entry.status() == ReportService.Status.RESOLVED) {
            details.add("");
            details.add("&7Resolved by: &f" + entry.resolvedBy());
            details.add("&7Resolved at: &f" + entry.resolvedAt());
        }
        inventory.setItem(13,''','''        if (entry.status() == ReportService.Status.RESOLVED) {
            details.add("");
            details.add("&7Resolved by: &f" + entry.resolvedBy());
            details.add("&7Resolved at: &f" + entry.resolvedAt());
        }
        if (!entry.notes().isEmpty()) {
            ReportService.StaffNote note = entry.notes().get(entry.notes().size() - 1);
            details.add("");
            details.add("&eLatest note: &f" + shorten(note.text(), 60));
            details.add("&8oleh " + note.staff());
        }
        details.add("&7Audit: &f" + entry.audit().size() + " &8| &7Notes: &f" + entry.notes().size());
        inventory.setItem(13,''','java notes detail')
# Add lore helper note command on detail in slot 22 if free (27 inventory).
s=replace_once(s,'''        if (plugin.getConfig().getBoolean("integrations.report.center.allow-delete", true)) {
            inventory.setItem(16, navigationItem(Material.BARRIER, "&cHapus Report", REPORT_DELETE, "&7Hapus laporan ini permanen."));
        }
        player.openInventory(inventory);''','''        if (plugin.getConfig().getBoolean("integrations.report.center.allow-delete", true)) {
            inventory.setItem(16, navigationItem(Material.BARRIER, "&cHapus Report", REPORT_DELETE, "&7Hapus laporan ini permanen."));
        }
        inventory.setItem(22, item(Material.PAPER, "&eStaff Note / Audit", List.of(
                "&7Tambah note lewat command:",
                "&f/cdrmemberbook report note " + reportId + " <catatan>",
                "",
                "&7Lihat audit:",
                "&f/cdrmemberbook report audit " + reportId
        )));
        player.openInventory(inventory);''','java note help')
write(p,s)

# Changelog/README
p='CHANGELOG.md'; s=read(p); s=s.replace('# Changelog\n','# Changelog\n\n## 1.9.5 - Report QoL & Audit\n\n- Added anti-duplicate reporter-to-target window with existing report ID feedback.\n- Added reporter/target/ANY search, recent reports, per-player report statistics and target report counts.\n- Added persistent staff notes and bounded audit history for CREATE/RESOLVE/REOPEN/NOTE actions.\n- Added Bedrock Report Center search, recent reports and native staff-note input.\n- Added Java recent reports plus richer report detail with counts, notes and audit metadata.\n- Added admin report `note` and `audit` actions plus `reports search`, `recent`, and `player` lookup commands.\n\n'); write(p,s)
p='README.md'; s=read(p); s=s.replace('# CdrMemberBook v1.9.3','# CdrMemberBook v1.9.5'); s=s.replace('- Java inventory GUI fallback.','- Java inventory GUI yang rapi untuk `/menu`, termasuk native Staff Report Center.\n- Report QoL & Audit: search, recent, per-player counts, staff notes, audit history, dan anti-duplicate report.'); write(p,s)

print('v1.9.5 patch applied')
