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
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

public final class ReportService {
    private final CdrMemberBookPlugin plugin;
    private final File file;
    private final YamlConfiguration data;
    private final Map<UUID, Long> cooldownUntil = new HashMap<>();

    public ReportService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.file = new File(plugin.getDataFolder(), "reports.yml");
        this.data = YamlConfiguration.loadConfiguration(file);
    }

    public boolean enabled() {
        return plugin.getConfig().getBoolean("integrations.report.enabled", true);
    }

    public SubmitResult submit(Player reporter, Player target, String rawReason) {
        if (!enabled()) return new SubmitResult(false, 0, 0, "disabled");
        if (reporter.getUniqueId().equals(target.getUniqueId())) return new SubmitResult(false, 0, 0, "self");
        String reason = rawReason == null ? "" : rawReason.trim();
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) return new SubmitResult(false, 0, 0, "short");
        if (reason.length() > max) reason = reason.substring(0, max);

        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(reporter.getUniqueId(), 0L);
        if (until > now) {
            long seconds = Math.max(1L, (until - now + 999L) / 1000L);
            return new SubmitResult(false, 0, seconds, "cooldown");
        }

        int id = Math.max(1, data.getInt("next-id", 1));
        String base = "reports." + id + ".";
        data.set(base + "status", Status.OPEN.name());
        data.set(base + "created-at", Instant.now().toString());
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
        data.set("next-id", id + 1);
        save();

        long cooldown = Math.max(0L, plugin.getConfig().getLong("integrations.report.cooldown-seconds", 60L));
        if (cooldown > 0L) cooldownUntil.put(reporter.getUniqueId(), now + cooldown * 1000L);
        notifyStaff(id, reporter, target, reason);
        runConsoleHook(id, reporter, target, reason);
        plugin.getLogger().info("Report #" + id + ": " + reporter.getName() + " -> " + target.getName() + " | " + reason);
        return new SubmitResult(true, id, 0, "ok");
    }

    public ReportEntry get(int id) {
        String base = "reports." + id;
        if (!data.isConfigurationSection(base)) return null;
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

    public int count(Status filter) {
        return list(filter).size();
    }

    public boolean resolve(int id, String staff) {
        ReportEntry entry = get(id);
        if (entry == null) return false;
        String base = "reports." + id + ".";
        data.set(base + "status", Status.RESOLVED.name());
        data.set(base + "resolved-at", Instant.now().toString());
        data.set(base + "resolved-by", staff == null || staff.isBlank() ? "Console" : staff);
        save();
        return true;
    }

    public boolean reopen(int id, String staff) {
        ReportEntry entry = get(id);
        if (entry == null) return false;
        String base = "reports." + id + ".";
        data.set(base + "status", Status.OPEN.name());
        data.set(base + "resolved-at", null);
        data.set(base + "resolved-by", null);
        save();
        plugin.getLogger().info("Report #" + id + " reopened by " + (staff == null ? "Console" : staff));
        return true;
    }

    public boolean delete(int id) {
        if (get(id) == null) return false;
        data.set("reports." + id, null);
        save();
        return true;
    }

    public Status parseStatus(String raw) {
        if (raw == null || raw.isBlank() || raw.equalsIgnoreCase("all")) return null;
        try { return Status.valueOf(raw.trim().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { return null; }
    }

    private ReportEntry readEntry(int id) {
        String base = "reports." + id + ".";
        if (!data.isConfigurationSection("reports." + id)) return null;
        Status status;
        try { status = Status.valueOf(data.getString(base + "status", "OPEN").toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { status = Status.OPEN; }
        return new ReportEntry(id, status,
                data.getString(base + "created-at", "unknown"),
                data.getString(base + "reporter.name", "unknown"), data.getString(base + "reporter.uuid", ""),
                data.getString(base + "target.name", "unknown"), data.getString(base + "target.uuid", ""),
                data.getString(base + "reason", ""), data.getString(base + "world", "unknown"),
                data.getInt(base + "location.x"), data.getInt(base + "location.y"), data.getInt(base + "location.z"),
                data.getString(base + "resolved-at", ""), data.getString(base + "resolved-by", ""));
    }

    private void notifyStaff(int id, Player reporter, Player target, String reason) {
        String permission = plugin.getConfig().getString("integrations.report.staff-permission", "cdrmemberbook.staff.report");
        String message = "&8[&cREPORT #" + id + "&8] &f" + reporter.getName() + " &7melaporkan &f"
                + target.getName() + "&7: &f" + reason;
        for (Player online : Bukkit.getOnlinePlayers()) {
            if (permission == null || permission.isBlank() || online.hasPermission(permission)) online.sendMessage(Colors.legacy(message));
        }
    }

    private void runConsoleHook(int id, Player reporter, Player target, String reason) {
        String template = plugin.getConfig().getString("integrations.report.console-command", "");
        if (template == null || template.isBlank()) return;
        String command = template.replace("%id%", Integer.toString(id)).replace("%reporter%", reporter.getName())
                .replace("%target%", target.getName()).replace("%reason%", reason.replace('\n', ' '));
        if (command.startsWith("/")) command = command.substring(1);
        Bukkit.dispatchCommand(Bukkit.getConsoleSender(), command);
    }

    private void save() {
        try { data.save(file); }
        catch (IOException exception) { plugin.getLogger().warning("Could not save reports.yml: " + exception.getMessage()); }
    }

    public enum Status { OPEN, RESOLVED }
    public record SubmitResult(boolean success, int id, long waitSeconds, String reasonCode) { }
    public record ReportEntry(int id, Status status, String createdAt, String reporterName, String reporterUuid,
                              String targetName, String targetUuid, String reason, String world,
                              int x, int y, int z, String resolvedAt, String resolvedBy) { }
}
