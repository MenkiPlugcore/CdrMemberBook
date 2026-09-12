package id.cadera.memberbook.report;

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
        return submit(reporter, target, "OTHER", rawReason, "");
    }

    public SubmitResult submit(Player reporter, Player target, String rawCategory, String rawReason, String rawEvidence) {
        if (!enabled()) return new SubmitResult(false, 0, 0, "disabled");
        if (reporter.getUniqueId().equals(target.getUniqueId())) return new SubmitResult(false, 0, 0, "self");

        String category = categoriesEnabled() ? normalizeCategory(rawCategory) : "OTHER";
        if (categoriesEnabled() && !categories().contains(category)) return new SubmitResult(false, 0, 0, "category");
        String reason = sanitizeText(rawReason);
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) return new SubmitResult(false, 0, 0, "short");
        if (reason.length() > max) reason = reason.substring(0, max).trim();

        String evidence = plugin.getConfig().getBoolean("integrations.report.evidence.enabled", true)
                ? sanitizeText(rawEvidence) : "";
        String evidenceValidation = validateEvidence(evidence);
        if (!"ok".equals(evidenceValidation)) return new SubmitResult(false, 0, 0, evidenceValidation);

        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(reporter.getUniqueId(), 0L);
        if (until > now) return new SubmitResult(false, 0, Math.max(1L, (until - now + 999L) / 1000L), "cooldown");

        DuplicateMatch duplicate = findDuplicate(reporter.getUniqueId(), target.getUniqueId(), now);
        if (duplicate != null) return new SubmitResult(false, duplicate.id(), duplicate.waitSeconds(), "duplicate");

        int id = Math.max(1, data.getInt("next-id", 1));
        String base = "reports." + id + ".";
        String createdAt = Instant.now().toString();
        data.set(base + "status", Status.OPEN.name());
        data.set(base + "created-at", createdAt);
        data.set(base + "reporter.name", reporter.getName());
        data.set(base + "reporter.uuid", reporter.getUniqueId().toString());
        data.set(base + "target.name", target.getName());
        data.set(base + "target.uuid", target.getUniqueId().toString());
        data.set(base + "category", category);
        data.set(base + "reason", reason);
        data.set(base + "evidence", evidence);
        data.set(base + "world", reporter.getWorld().getName());
        data.set(base + "location.x", reporter.getLocation().getBlockX());
        data.set(base + "location.y", reporter.getLocation().getBlockY());
        data.set(base + "location.z", reporter.getLocation().getBlockZ());
        data.set(base + "resolved-at", null);
        data.set(base + "resolved-by", null);
        data.set(base + "notes", new ArrayList<>());
        data.set(base + "audit", new ArrayList<>());
        appendAuditInMemory(id, "CREATE", reporter.getName(), "[" + category + "] Report dibuat untuk " + target.getName());
        data.set("next-id", id + 1);
        if (!save()) {
            reloadFromDisk();
            return new SubmitResult(false, 0, 0, "storage");
        }

        long cooldown = Math.max(0L, plugin.getConfig().getLong("integrations.report.cooldown-seconds", 60L));
        if (cooldown > 0L) cooldownUntil.put(reporter.getUniqueId(), now + cooldown * 1000L);
        notifyStaff(id, reporter, target, category, reason, evidence);
        runConsoleHook(id, reporter, target, category, reason, evidence);
        plugin.getLogger().info("Report #" + id + " [" + category + "]: " + reporter.getName() + " -> " + target.getName() + " | " + reason);
        return new SubmitResult(true, id, 0, "ok");
    }

    public boolean categoriesEnabled() {
        return plugin.getConfig().getBoolean("integrations.report.categories.enabled", true);
    }

    public List<String> categories() {
        List<String> configured = plugin.getConfig().getStringList("integrations.report.categories.values");
        if (configured.isEmpty()) configured = List.of("CHEATING", "GRIEFING", "TOXIC", "SCAM", "BUG_ABUSE", "OTHER");
        List<String> out = new ArrayList<>();
        for (String raw : configured) {
            String normalized = normalizeCategory(raw);
            if (!normalized.isBlank() && !out.contains(normalized)) out.add(normalized);
        }
        if (out.isEmpty()) out.add("OTHER");
        return List.copyOf(out);
    }

    public String normalizeCategory(String raw) {
        String value = raw == null ? "" : raw.trim().toUpperCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        value = value.replaceAll("[^A-Z0-9_]", "");
        return value.isBlank() ? "OTHER" : value;
    }

    public String categoryLabel(String raw) {
        String category = normalizeCategory(raw);
        String configured = plugin.getConfig().getString("integrations.report.categories.labels." + category);
        if (configured != null && !configured.isBlank()) return configured;
        String[] parts = category.toLowerCase(Locale.ROOT).split("_");
        StringBuilder out = new StringBuilder();
        for (String part : parts) {
            if (part.isBlank()) continue;
            if (out.length() > 0) out.append(' ');
            out.append(Character.toUpperCase(part.charAt(0))).append(part.substring(1));
        }
        return out.length() == 0 ? "Other" : out.toString();
    }

    public String validateEvidence(String rawEvidence) {
        if (!plugin.getConfig().getBoolean("integrations.report.evidence.enabled", true)) return "ok";
        String evidence = sanitizeText(rawEvidence);
        boolean optional = plugin.getConfig().getBoolean("integrations.report.evidence.optional", true);
        if (evidence.isBlank()) return optional ? "ok" : "evidence-required";
        int max = Math.max(20, plugin.getConfig().getInt("integrations.report.evidence.max-length", 300));
        if (evidence.length() > max) return "evidence-too-long";
        if (plugin.getConfig().getBoolean("integrations.report.evidence.require-http-url-if-link", true)
                && evidence.matches("(?i)^[a-z][a-z0-9+.-]*://.*")
                && !(evidence.toLowerCase(Locale.ROOT).startsWith("http://") || evidence.toLowerCase(Locale.ROOT).startsWith("https://"))) {
            return "evidence-invalid-link";
        }
        return "ok";
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
                    || contains(entry.targetName(), needle) || contains(entry.targetUuid(), needle)
                    || contains(entry.category(), needle) || contains(entry.evidence(), needle);
        }).toList();
    }

    public List<ReportEntry> listByCategory(String rawCategory, Status filter) {
        String category = normalizeCategory(rawCategory);
        return list(filter).stream().filter(entry -> normalizeCategory(entry.category()).equals(category)).toList();
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
                normalizeCategory(data.getString(base + "category", "OTHER")), data.getString(base + "reason", ""),
                data.getString(base + "evidence", ""), data.getString(base + "world", "unknown"),
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

    private void notifyStaff(int id, Player reporter, Player target, String category, String reason, String evidence) {
        String permission = plugin.getConfig().getString("integrations.report.staff-permission", "cdrmemberbook.staff.report");
        String message = "&8[&cREPORT #" + id + "&8] &7[&e" + category + "&7] &f" + reporter.getName()
                + " &7melaporkan &f" + target.getName() + "&7: &f" + reason
                + (evidence.isBlank() ? "" : " &8| &7Evidence: &f" + evidence);
        for (Player online : Bukkit.getOnlinePlayers()) {
            if (permission != null && !permission.isBlank() && !online.hasPermission(permission)) continue;
            if (plugin.preferences() != null && !plugin.preferences().reportStaffNotificationsEnabled(online)) continue;
            online.sendMessage(Colors.legacy(message));
        }
    }

    private void runConsoleHook(int id, Player reporter, Player target, String category, String reason, String evidence) {
        String template = plugin.getConfig().getString("integrations.report.console-command", "");
        if (template == null || template.isBlank()) return;
        String command = template.replace("%id%", Integer.toString(id)).replace("%reporter%", reporter.getName())
                .replace("%target%", target.getName()).replace("%category%", category)
                .replace("%reason%", reason).replace("%evidence%", evidence);
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
                              String targetName, String targetUuid, String category, String reason, String evidence, String world,
                              int x, int y, int z, String resolvedAt, String resolvedBy,
                              List<StaffNote> notes, List<AuditEntry> audit) { }
    private record DuplicateMatch(int id, long waitSeconds) { }
}
