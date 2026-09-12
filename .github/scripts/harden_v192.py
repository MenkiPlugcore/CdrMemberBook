from pathlib import Path
import re

root = Path('.')

def read(p): return (root / p).read_text()
def write(p,s): (root / p).write_text(s)
def repl(s, old, new, label):
    if old not in s: raise SystemExit(f'pattern not found: {label}')
    return s.replace(old,new,1)

# Versions
s=read('pom.xml'); s=repl(s,'<version>1.9.1</version>','<version>1.9.2</version>','pom version'); write('pom.xml',s)
s=read('src/main/resources/plugin.yml'); s=repl(s,"version: '1.9.1'","version: '1.9.2'",'plugin version'); write('src/main/resources/plugin.yml',s)

# Harden action runner.
write('src/main/java/id/cadera/memberbook/menu/MenuActionService.java', r'''package id.cadera.memberbook.menu;

import id.cadera.memberbook.CdrMemberBookPlugin;
import org.bukkit.Sound;
import org.bukkit.entity.Player;

import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

public final class MenuActionService {
    private final CdrMemberBookPlugin plugin;
    private final Map<UUID, Long> generations = new HashMap<>();
    private final Map<UUID, Long> cooldownUntil = new HashMap<>();

    public MenuActionService(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    public boolean execute(Player player, List<MenuConfigService.MenuAction> actions) {
        if (actions == null || actions.isEmpty()) return false;
        if (!plugin.getConfig().getBoolean("menu.actions.enabled", true)) return false;

        int maxActions = Math.max(1, plugin.getConfig().getInt("menu.actions.max-actions-per-chain", 32));
        if (actions.size() > maxActions) {
            plugin.getLogger().warning("Blocked menu action chain for " + player.getName()
                    + ": " + actions.size() + " actions exceeds max " + maxActions + ".");
            plugin.message(player, "action-chain-invalid");
            return false;
        }

        long maxDelay = Math.max(0L, plugin.getConfig().getLong("menu.actions.max-total-delay-ticks", 1200L));
        long totalDelay = 0L;
        for (MenuConfigService.MenuAction action : actions) {
            if (!"delay".equalsIgnoreCase(action.type())) continue;
            long ticks = Math.max(1L, action.ticks());
            if (ticks > maxDelay || totalDelay > maxDelay - ticks) {
                plugin.getLogger().warning("Blocked menu action chain for " + player.getName()
                        + ": total delay exceeds " + maxDelay + " ticks.");
                plugin.message(player, "action-chain-invalid");
                return false;
            }
            totalDelay += ticks;
        }

        UUID uuid = player.getUniqueId();
        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(uuid, 0L);
        if (until > now) {
            plugin.message(player, "action-chain-cooldown");
            return false;
        }
        long cooldownTicks = Math.max(0L, plugin.getConfig().getLong("menu.actions.click-cooldown-ticks", 10L));
        if (cooldownTicks > 0L) cooldownUntil.put(uuid, now + cooldownTicks * 50L);

        // Starting a new chain supersedes delayed continuations from an older chain.
        long token = generations.getOrDefault(uuid, 0L) + 1L;
        generations.put(uuid, token);
        run(uuid, token, actions, 0);
        return true;
    }

    private void run(UUID uuid, long token, List<MenuConfigService.MenuAction> actions, int index) {
        if (!isCurrent(uuid, token) || index >= actions.size()) return;
        Player player = plugin.getServer().getPlayer(uuid);
        if (player == null || !player.isOnline()) {
            cancel(uuid);
            return;
        }

        MenuConfigService.MenuAction action = actions.get(index);
        String type = action.type() == null ? "" : action.type().toLowerCase(Locale.ROOT);
        if ("delay".equals(type)) {
            long ticks = Math.max(1L, action.ticks());
            plugin.getServer().getScheduler().runTaskLater(plugin,
                    () -> run(uuid, token, actions, index + 1), ticks);
            return;
        }

        boolean failed = false;
        try {
            switch (type) {
                case "command" -> plugin.dispatchActionCommand(player, action.value(), action.executor());
                case "console-command" -> plugin.dispatchActionCommand(player, action.value(), "console");
                case "message" -> player.sendMessage(plugin.formatMenuText(action.value(), player));
                case "sound" -> {
                    Sound sound = Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT));
                    player.playSound(player.getLocation(), sound, action.volume(), action.pitch());
                }
                case "close" -> player.closeInventory();
                case "open-menu" -> plugin.openMenu(player, action.value());
                default -> {
                    failed = true;
                    plugin.getLogger().warning("Unknown menu action type: " + action.type());
                }
            }
        } catch (Throwable throwable) {
            failed = true;
            plugin.getLogger().warning("Menu action failed for " + player.getName() + " [" + action.type()
                    + "]: " + throwable.getClass().getSimpleName() + ": " + throwable.getMessage());
        }

        if (failed && plugin.getConfig().getBoolean("menu.actions.stop-on-error", false)) {
            generations.remove(uuid);
            return;
        }
        run(uuid, token, actions, index + 1);
    }

    private boolean isCurrent(UUID uuid, long token) {
        return generations.getOrDefault(uuid, -1L) == token;
    }

    public void cancel(UUID uuid) {
        generations.remove(uuid);
        cooldownUntil.remove(uuid);
    }

    public void shutdown() {
        generations.clear();
        cooldownUntil.clear();
    }
}
''')

# Harden report persistence.
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
        String reason = sanitizeReason(rawReason);
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) return new SubmitResult(false, 0, 0, "short");
        if (reason.length() > max) reason = reason.substring(0, max).trim();

        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(reporter.getUniqueId(), 0L);
        if (until > now) return new SubmitResult(false, 0, Math.max(1L, (until - now + 999L) / 1000L), "cooldown");

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

    public int count(Status filter) { return list(filter).size(); }

    public boolean resolve(int id, String staff) {
        if (get(id) == null) return false;
        String base = "reports." + id + ".";
        data.set(base + "status", Status.RESOLVED.name());
        data.set(base + "resolved-at", Instant.now().toString());
        data.set(base + "resolved-by", safeStaff(staff));
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
        if (!save()) { reloadFromDisk(); return false; }
        plugin.getLogger().info("Report #" + id + " reopened by " + safeStaff(staff));
        return true;
    }

    public boolean delete(int id) {
        if (get(id) == null) return false;
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

    private ReportEntry readEntry(int id) {
        String base = "reports." + id + ".";
        if (!data.isConfigurationSection("reports." + id)) return null;
        Status status;
        try { status = Status.valueOf(data.getString(base + "status", "OPEN").toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { status = Status.OPEN; }
        return new ReportEntry(id, status, data.getString(base + "created-at", "unknown"),
                data.getString(base + "reporter.name", "unknown"), data.getString(base + "reporter.uuid", ""),
                data.getString(base + "target.name", "unknown"), data.getString(base + "target.uuid", ""),
                data.getString(base + "reason", ""), data.getString(base + "world", "unknown"),
                data.getInt(base + "location.x"), data.getInt(base + "location.y"), data.getInt(base + "location.z"),
                data.getString(base + "resolved-at", ""), data.getString(base + "resolved-by", ""));
    }

    private String sanitizeReason(String raw) {
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
    public record SubmitResult(boolean success, int id, long waitSeconds, String reasonCode) { }
    public record ReportEntry(int id, Status status, String createdAt, String reporterName, String reporterUuid,
                              String targetName, String targetUuid, String reason, String world,
                              int x, int y, int z, String resolvedAt, String resolvedBy) { }
}
''')

# MenuConfigService targeted hardening.
p='src/main/java/id/cadera/memberbook/menu/MenuConfigService.java'; s=read(p)
s=repl(s,'private static final Set<String> ACTION_TYPES = Set.of("command", "console-command", "message", "sound", "close", "open-menu", "delay");',
'''private static final Set<String> ACTION_TYPES = Set.of("command", "console-command", "message", "sound", "close", "open-menu", "delay");
    private static final Set<String> CONDITION_OPERATORS = Set.of("==", "=", "equals", "!=", "not_equals", "contains", "not_contains", "starts_with", "ends_with", ">", ">=", "<", "<=");''','condition operators')
s=repl(s,'    private List<MenuAction> parseActions(ConfigurationSection button) {\n        List<MenuAction> actions = new ArrayList<>();',
'''    private List<MenuAction> parseActions(ConfigurationSection button) {
        if (!plugin.getConfig().getBoolean("menu.actions.enabled", true)) return List.of();
        List<MenuAction> actions = new ArrayList<>();''','actions enabled')
s=repl(s,'        Availability condition = conditionsAvailability(player, button.conditions());\n        if (!condition.available()) return condition;',
'''        Availability condition;
        try { condition = conditionsAvailability(player, button.conditions()); }
        catch (Throwable throwable) {
            plugin.getLogger().warning("Menu condition evaluation failed [" + button.key() + "]: " + throwable.getMessage());
            return new Availability(false,"condition-error",throwable.getClass().getSimpleName());
        }
        if (!condition.available()) return condition;''','condition fail safe')
s=repl(s,'    private Availability conditionsAvailability(Player player, MenuConditions c) {\n        if (c == null) return new Availability(true,"ok","no-conditions");',
'''    private Availability conditionsAvailability(Player player, MenuConditions c) {
        if (c == null) return new Availability(true,"ok","no-conditions");
        int maxPlaceholderConditions = Math.max(1, plugin.getConfig().getInt("menu.conditions.max-placeholder-conditions", 16));
        if (c.placeholders().size() > maxPlaceholderConditions) return new Availability(false,"condition-too-many","max="+maxPlaceholderConditions);
        int maxValueLength = Math.max(32, plugin.getConfig().getInt("menu.conditions.max-value-length", 512));''','condition limits')
s=repl(s,'        for (PlaceholderCondition p : c.placeholders()) {\n            String left = resolveConditionText(player, p.value());\n            String right = resolveConditionText(player, p.compare());\n            if (!compare(left, p.operator(), right)) return new Availability(false,"condition-placeholder",p.value()+" "+p.operator()+" "+p.compare()+" (got="+left+")");\n        }',
'''        for (PlaceholderCondition p : c.placeholders()) {
            String op = p.operator() == null ? "==" : p.operator().trim().toLowerCase(Locale.ROOT);
            if (!CONDITION_OPERATORS.contains(op)) return new Availability(false,"condition-operator-invalid",op);
            if ((p.value()!=null && p.value().length()>maxValueLength) || (p.compare()!=null && p.compare().length()>maxValueLength))
                return new Availability(false,"condition-value-too-long","max="+maxValueLength);
            String left = resolveConditionText(player, p.value());
            String right = resolveConditionText(player, p.compare());
            if (left.length()>maxValueLength || right.length()>maxValueLength) return new Availability(false,"condition-result-too-long","max="+maxValueLength);
            if (!compare(left, op, right)) return new Availability(false,"condition-placeholder",p.value()+" "+p.operator()+" "+p.compare()+" (got="+left+")");
        }''','placeholder hardening')
s=repl(s,'    private Availability actionsAvailability(List<MenuAction> actions) {\n        for (MenuAction action : actions) {',
'''    private Availability actionsAvailability(List<MenuAction> actions) {
        int maxActions = Math.max(1, plugin.getConfig().getInt("menu.actions.max-actions-per-chain", 32));
        if (actions.size() > maxActions) return new Availability(false,"action-chain-too-large","max="+maxActions);
        long maxDelay = Math.max(0L, plugin.getConfig().getLong("menu.actions.max-total-delay-ticks", 1200L));
        long totalDelay = 0L;
        for (MenuAction action : actions) {
            if ("delay".equals(action.type())) {
                long ticks = Math.max(1L, action.ticks());
                if (ticks > maxDelay || totalDelay > maxDelay - ticks) return new Availability(false,"action-delay-too-large","max="+maxDelay);
                totalDelay += ticks;
            }''','action limits')
write(p,s)

# Main plugin version/config migration/lifecycle.
p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
s=repl(s,'getLogger().info("CdrMemberBook v1.9.1 enabled.");','getLogger().info("CdrMemberBook v1.9.2 enabled.");','startup version')
s=repl(s,'''    public void onDisable() {
        if (memberBookService != null) memberBookService.stopEnforcement();
    }''','''    public void onDisable() {
        if (memberBookService != null) memberBookService.stopEnforcement();
        if (menuActionService != null) menuActionService.shutdown();
    }''','disable actions')
s=repl(s,'''        if (configVersion < 18) {
            getConfig().set("menu.conditions.placeholderapi", true);
        }

        getConfig().set("config-version", 18);''','''        if (configVersion < 18) {
            getConfig().set("menu.conditions.placeholderapi", true);
        }

        if (configVersion < 19) {
            getConfig().set("menu.actions.click-cooldown-ticks", 10L);
            getConfig().set("menu.actions.max-actions-per-chain", 32);
            getConfig().set("menu.actions.max-total-delay-ticks", 1200L);
            getConfig().set("menu.actions.stop-on-error", false);
            getConfig().set("menu.conditions.max-placeholder-conditions", 16);
            getConfig().set("menu.conditions.max-value-length", 512);
            getConfig().set("integrations.report.sanitize-control-characters", true);
        }

        getConfig().set("config-version", 19);''','migration v19')
s=repl(s,'''    public void onQuit(PlayerQuitEvent event) {
        requestManager.removeRequestsFor(event.getPlayer().getUniqueId());
    }''','''    public void onQuit(PlayerQuitEvent event) {
        requestManager.removeRequestsFor(event.getPlayer().getUniqueId());
        if (menuActionService != null) menuActionService.cancel(event.getPlayer().getUniqueId());
    }''','quit action cleanup')
write(p,s)

# Admin command hardening + health.
p='src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'; s=read(p)
s=repl(s,'        if (action.equals("reports")) { handleReports(sender, args); return true; }\n        if (action.equals("report")) { handleReport(sender, args); return true; }',
'''        if (action.equals("reports")) { handleReports(sender, args); return true; }
        if (action.equals("report")) { handleReport(sender, args); return true; }
        if (action.equals("health")) { sendHealth(sender); return true; }''','health dispatch')
s=repl(s,'        try { id = Integer.parseInt(args[2]); } catch (NumberFormatException ex) { sender.sendMessage(Colors.legacy("&cID report tidak valid.")); return; }',
'''        try { id = Integer.parseInt(args[2]); } catch (NumberFormatException ex) { sender.sendMessage(Colors.legacy("&cID report tidak valid.")); return; }
        if (id <= 0) { sender.sendMessage(Colors.legacy("&cID report harus lebih dari 0.")); return; }''','positive report id')
s=repl(s,'''            case "resolve" -> { plugin.reports().resolve(id, staff); sender.sendMessage(Colors.legacy("&aReport #" + id + " ditandai RESOLVED.")); }
            case "reopen" -> { plugin.reports().reopen(id, staff); sender.sendMessage(Colors.legacy("&eReport #" + id + " dibuka kembali.")); }
            case "delete" -> { plugin.reports().delete(id); sender.sendMessage(Colors.legacy("&aReport #" + id + " dihapus.")); }''','''            case "resolve" -> sender.sendMessage(Colors.legacy(plugin.reports().resolve(id, staff)
                    ? "&aReport #" + id + " ditandai RESOLVED." : "&cGagal menyimpan perubahan report #" + id + "."));
            case "reopen" -> sender.sendMessage(Colors.legacy(plugin.reports().reopen(id, staff)
                    ? "&eReport #" + id + " dibuka kembali." : "&cGagal menyimpan perubahan report #" + id + "."));
            case "delete" -> sender.sendMessage(Colors.legacy(plugin.reports().delete(id)
                    ? "&aReport #" + id + " dihapus." : "&cGagal menghapus report #" + id + "."));''','report persistence feedback')
s=repl(s,'    private String shorten(String value, int max) { return value.length() <= max ? value : value.substring(0, max - 3) + "..."; }',
'''    private void sendHealth(CommandSender sender) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook Health &8- &fv1.9.2"));
        sender.sendMessage(Colors.legacy("&7Config version: &f" + plugin.getConfig().getInt("config-version", -1)
                + " &8| &7Actions: &f" + plugin.getConfig().getBoolean("menu.actions.enabled", true)));
        sender.sendMessage(Colors.legacy("&7Floodgate: &f" + Bukkit.getPluginManager().isPluginEnabled("floodgate")
                + " &8| &7PlaceholderAPI: &f" + Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI")));
        sender.sendMessage(Colors.legacy("&7EssentialsX: &f" + Bukkit.getPluginManager().isPluginEnabled("Essentials")
                + " &8| &7AxTrade: &f" + Bukkit.getPluginManager().isPluginEnabled("AxTrade")));
        sender.sendMessage(Colors.legacy("&7Reports: &f" + plugin.reports().enabled()
                + " &8| &7Open: &f" + plugin.reports().count(ReportService.Status.OPEN)
                + " &8| &7Resolved: &f" + plugin.reports().count(ReportService.Status.RESOLVED)));
        sender.sendMessage(Colors.legacy("&7Action limits: &f" + plugin.getConfig().getInt("menu.actions.max-actions-per-chain", 32)
                + " actions &8/ &f" + plugin.getConfig().getLong("menu.actions.max-total-delay-ticks", 1200L) + " ticks delay"));
    }

    private String shorten(String value, int max) {
        if (value == null) return "";
        return value.length() <= max ? value : value.substring(0, Math.max(0, max - 3)) + "...";
    }''','health method')
s=s.replace('&fv1.9.1 &8- &7Admin Tools','&fv1.9.2 &8- &7Admin Tools')
s=repl(s,'        sender.sendMessage(Colors.legacy("&f/" + label + " report <view|resolve|reopen|delete> <id>"));',
'''        sender.sendMessage(Colors.legacy("&f/" + label + " report <view|resolve|reopen|delete> <id>"));
        sender.sendMessage(Colors.legacy("&f/" + label + " health &8- &7cek dependency + production limits"));''','usage health')
s=repl(s,'return List.of("give","remove","fix","refresh","status","menudebug","tutorialreset","tutorialshow","reports","report")',
'return List.of("give","remove","fix","refresh","status","menudebug","tutorialreset","tutorialshow","reports","report","health")','tab health')
write(p,s)

# Config defaults.
p='src/main/resources/config.yml'; s=read(p)
s=s.replace('# CdrMemberBook v1.9.1','# CdrMemberBook v1.9.2',1).replace('config-version: 18','config-version: 19',1)
s=repl(s,'''  actions:
    enabled: true
  conditions:
    # Izinkan PlaceholderAPI untuk evaluasi conditions.placeholder(s).
    placeholderapi: true''','''  actions:
    enabled: true
    # Anti-spam click untuk action chain. 10 ticks = 0.5 detik.
    click-cooldown-ticks: 10
    # Safety caps agar config yang salah tidak membuat chain/scheduler berlebihan.
    max-actions-per-chain: 32
    max-total-delay-ticks: 1200
    # false = action berikutnya tetap dicoba jika satu action gagal.
    stop-on-error: false
  conditions:
    # Izinkan PlaceholderAPI untuk evaluasi conditions.placeholder(s).
    placeholderapi: true
    max-placeholder-conditions: 16
    max-value-length: 512''','config action limits')
s=repl(s,'    max-reason-length: 200\n    # Jumlah report per halaman',
'''    max-reason-length: 200
    # Bersihkan newline/control character dari alasan sebelum disimpan/log/hook.
    sanitize-control-characters: true
    # Jumlah report per halaman''','report sanitize config')
s=repl(s,"  action-disabled: '&eFitur ini belum diaktifkan atau command tombol masih kosong.'",
'''  action-disabled: '&eFitur ini belum diaktifkan atau command tombol masih kosong.'
  action-chain-cooldown: '&eTunggu sebentar sebelum menekan action menu lagi.'
  action-chain-invalid: '&cAction menu diblok karena melewati batas keamanan config.' ''','action messages')
# fix accidental trailing YAML quote spacing safely
s=s.replace("  action-chain-invalid: '&cAction menu diblok karena melewati batas keamanan config.' '","  action-chain-invalid: '&cAction menu diblok karena melewati batas keamanan config.'")
write(p,s)

# README / changelog
p='README.md'; s=read(p); s=s.replace('# CdrMemberBook v1.9.1','# CdrMemberBook v1.9.2',1)
if '## Production Hardening v1.9.2' not in s:
    s += '''\n\n## Production Hardening v1.9.2\n\n- Action chain sekarang memiliki click cooldown, batas jumlah action, batas total delay, supersede chain lama, dan opsi `stop-on-error`.\n- `menu.actions.enabled` sekarang benar-benar mematikan advanced action list dan mengembalikan tombol ke legacy action/type.\n- Menu conditions dibatasi jumlah placeholder dan panjang value/result agar expansion/config bermasalah tidak membebani render menu.\n- Report hanya dianggap berhasil setelah `reports.yml` benar-benar tersimpan; mutation resolve/reopen/delete juga melaporkan kegagalan storage.\n- Reason report dibersihkan dari control character sebelum disimpan/log/hook.\n- `/cdrmemberbook health` menampilkan dependency, report count, config version, dan action safety limits.\n'''
write(p,s)
p='CHANGELOG.md'; s=read(p)
if '## 1.9.2 - Production Hardening' not in s:
    entry='''\n## 1.9.2 - Production Hardening\n\n- Added guarded/cancellable menu action chains with anti-spam cooldown and safety caps.\n- Made `menu.actions.enabled` authoritative at runtime.\n- Added fail-safe and resource limits for advanced menu conditions.\n- Hardened report persistence so success is only returned after a successful disk save.\n- Sanitized report reasons and hardened report admin mutation feedback.\n- Added `/cdrmemberbook health` production diagnostics.\n\n'''
    s=repl(s,'# Changelog\n','# Changelog\n'+entry,'changelog')
write(p,s)

print('v1.9.2 hardening applied')
