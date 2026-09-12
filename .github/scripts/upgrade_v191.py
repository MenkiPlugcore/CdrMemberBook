from pathlib import Path
import sys, re

root = Path('.')
stage = sys.argv[1]


def read(p): return (root / p).read_text()
def write(p, s): (root / p).write_text(s)
def replace_once(s, old, new, label):
    if old not in s:
        raise SystemExit(f'pattern not found: {label}')
    return s.replace(old, new, 1)

def set_version(version, config_version):
    pom = read('pom.xml')
    pom = re.sub(r'<version>1\.(?:8|9)\.\d+</version>', f'<version>{version}</version>', pom, count=1)
    write('pom.xml', pom)
    py = read('src/main/resources/plugin.yml')
    py = re.sub(r"version: '1\.(?:8|9)\.\d+'", f"version: '{version}'", py, count=1)
    write('src/main/resources/plugin.yml', py)
    cfg = read('src/main/resources/config.yml')
    cfg = re.sub(r'# CdrMemberBook v1\.(?:8|9)\.\d+', f'# CdrMemberBook v{version}', cfg, count=1)
    cfg = re.sub(r'config-version: \d+', f'config-version: {config_version}', cfg, count=1)
    write('src/main/resources/config.yml', cfg)
    rd = read('README.md')
    rd = re.sub(r'^# CdrMemberBook v1\.(?:8|9)\.\d+', f'# CdrMemberBook v{version}', rd, count=1, flags=re.M)
    write('README.md', rd)


def add_changelog(version, title, bullets):
    p = 'CHANGELOG.md'
    s = read(p)
    marker = f'## {version} - {title}'
    if marker in s: return
    entry = '\n' + marker + '\n\n' + ''.join(f'- {b}\n' for b in bullets) + '\n'
    s = replace_once(s, '# Changelog\n', '# Changelog\n' + entry, f'changelog {version}')
    write(p, s)


def patch_main_migration(version, from_cv, to_cv, body_lines):
    p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
    s=read(p)
    s=re.sub(r'getLogger\(\)\.info\("CdrMemberBook v1\.(?:8|9)\.\d+ enabled\."\);', f'getLogger().info("CdrMemberBook v{version} enabled.");', s, count=1)
    old=f'''        getConfig().set("config-version", {from_cv});\n        saveConfig();\n    }}\n'''
    body='\n'.join('            '+line for line in body_lines)
    new=f'''        if (configVersion < {to_cv}) {{\n{body}\n        }}\n\n        getConfig().set("config-version", {to_cv});\n        saveConfig();\n    }}\n'''
    s=replace_once(s, old, new, f'main migration {from_cv}->{to_cv}')
    write(p,s)


MENU_183 = r'''package id.cadera.memberbook.menu;

import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import id.cadera.memberbook.CdrMemberBookPlugin;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class MenuConfigService {
    private static final Set<String> KNOWN_TYPES = Set.of(
            "command", "teleport", "homes", "pay", "trade", "report", "submenu", "close");
    private final CdrMemberBookPlugin plugin;

    public MenuConfigService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    public MenuDefinition getMenu(String menuId) {
        String normalized = normalizeMenuId(menuId);
        String path = normalized.equals("main") ? "menu.main" : "menu.submenus." + normalized;
        ConfigurationSection section = plugin.getConfig().getConfigurationSection(path);
        if (section == null) return null;

        String title = section.getString("title", normalized.equals("main")
                ? "CdrMemberBook • Menu Member"
                : normalized);
        String content = section.getString("content", "");
        String backMenu = normalizeMenuId(section.getString("back-menu", "main"));

        List<MenuButton> buttons = new ArrayList<>();
        ConfigurationSection buttonSection = section.getConfigurationSection("buttons");
        if (buttonSection != null) {
            for (String key : buttonSection.getKeys(false)) {
                ConfigurationSection button = buttonSection.getConfigurationSection(key);
                if (button == null || !button.getBoolean("enabled", true)) continue;
                String type = button.getString("type", "command");
                if (type == null) type = "command";
                type = type.trim().toLowerCase(Locale.ROOT);
                buttons.add(new MenuButton(
                        key,
                        button.getString("name", key),
                        type,
                        button.getString("command", ""),
                        button.getString("executor", "player"),
                        button.getString("submenu", ""),
                        button.getString("icon", ""),
                        button.getString("java-material", "PAPER"),
                        button.getString("permission", ""),
                        button.getInt("order", 100),
                        button.getStringList("lore"),
                        button.getStringList("requires-plugins"),
                        button.getString("requires-command", ""),
                        button.getBoolean("auto-detect-command", true)
                ));
            }
        }
        buttons.sort(Comparator.comparingInt(MenuButton::order).thenComparing(MenuButton::key));
        return new MenuDefinition(normalized, title == null ? "" : title,
                content == null ? "" : content, backMenu, List.copyOf(buttons));
    }

    public List<MenuButton> visibleButtons(MenuDefinition menu, Player player) {
        boolean hideWithoutPermission = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);
        return menu.buttons().stream()
                .filter(button -> !hideWithoutPermission || canUse(player, button))
                .filter(button -> !hideUnavailable || availability(player, button).available())
                .toList();
    }

    public boolean canUse(Player player, MenuButton button) {
        String permission = button.permission();
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }

    public boolean isAvailable(Player player, MenuButton button) {
        return availability(player, button).available();
    }

    public Availability availability(Player player, MenuButton button) {
        if (!KNOWN_TYPES.contains(button.type())) return new Availability(false, "invalid-type", "type=" + button.type());
        for (String pluginName : button.requiredPlugins()) {
            if (pluginName == null || pluginName.isBlank()) continue;
            if (!plugin.getServer().getPluginManager().isPluginEnabled(pluginName.trim())) {
                return new Availability(false, "missing-plugin", pluginName.trim());
            }
        }
        if (button.requiredCommand() != null && !button.requiredCommand().isBlank()
                && !commandAvailable(button.requiredCommand())) {
            return new Availability(false, "missing-command", rootCommand(button.requiredCommand()));
        }

        return switch (button.type()) {
            case "teleport", "close" -> new Availability(true, "ok", "built-in");
            case "submenu" -> {
                if (button.submenu() == null || button.submenu().isBlank())
                    yield new Availability(false, "missing-submenu", "submenu kosong");
                yield getMenu(button.submenu()) == null
                        ? new Availability(false, "missing-submenu", button.submenu())
                        : new Availability(true, "ok", "submenu=" + button.submenu());
            }
            case "homes" -> plugin.homes() != null && plugin.homes().available()
                    ? new Availability(true, "ok", "EssentialsX")
                    : new Availability(false, "missing-integration", "EssentialsX Home");
            case "pay" -> commandAvailable(plugin.getConfig().getString(
                    "integrations.pay.command", "pay %target% %amount%"))
                    ? new Availability(true, "ok", "pay command")
                    : new Availability(false, "missing-command", rootCommand(plugin.getConfig().getString(
                    "integrations.pay.command", "pay %target% %amount%")));
            case "trade" -> {
                if (!plugin.getServer().getPluginManager().isPluginEnabled("AxTrade"))
                    yield new Availability(false, "missing-plugin", "AxTrade");
                String command = plugin.getConfig().getString("integrations.axtrade.send-command", "axtrade %target%");
                yield commandAvailable(command)
                        ? new Availability(true, "ok", "AxTrade")
                        : new Availability(false, "missing-command", rootCommand(command));
            }
            case "report" -> {
                boolean nativeBedrock = plugin.reports() != null && plugin.reports().enabled()
                        && plugin.forms() != null && plugin.forms().isBedrock(player);
                if (nativeBedrock) yield new Availability(true, "ok", "native-report");
                yield commandAvailable(button.command())
                        ? new Availability(true, "ok", "external-report")
                        : new Availability(false, "missing-command", rootCommand(button.command()));
            }
            case "command" -> {
                if (button.command() == null || button.command().isBlank())
                    yield new Availability(false, "empty-command", "command kosong");
                if (!plugin.getConfig().getBoolean("menu.auto-detect-command-dependencies", true)
                        || !button.autoDetectCommand()) yield new Availability(true, "ok", "auto-detect off");
                yield commandAvailable(button.command())
                        ? new Availability(true, "ok", "command=" + rootCommand(button.command()))
                        : new Availability(false, "missing-command", rootCommand(button.command()));
            }
            default -> new Availability(false, "invalid-type", button.type());
        };
    }

    public void validateConfiguration() {
        if (!plugin.getConfig().getBoolean("menu.log-invalid-buttons", true)) return;
        List<String> menuIds = new ArrayList<>();
        menuIds.add("main");
        ConfigurationSection submenus = plugin.getConfig().getConfigurationSection("menu.submenus");
        if (submenus != null) menuIds.addAll(submenus.getKeys(false));
        for (String menuId : menuIds) {
            MenuDefinition menu = getMenu(menuId);
            if (menu == null) continue;
            for (MenuButton button : menu.buttons()) {
                if (!KNOWN_TYPES.contains(button.type()))
                    warn(menuId, button.key(), "type tidak dikenal: " + button.type());
                if ("command".equals(button.type()) && (button.command() == null || button.command().isBlank()))
                    warn(menuId, button.key(), "type command tetapi command kosong");
                if ("submenu".equals(button.type()) && (button.submenu() == null || button.submenu().isBlank()))
                    warn(menuId, button.key(), "type submenu tetapi submenu kosong");
                if ("submenu".equals(button.type()) && button.submenu() != null && !button.submenu().isBlank()
                        && getMenu(button.submenu()) == null)
                    warn(menuId, button.key(), "submenu tidak ditemukan: " + button.submenu());
                String executor = button.executor() == null ? "player" : button.executor().trim().toLowerCase(Locale.ROOT);
                if (!executor.equals("player") && !executor.equals("console"))
                    warn(menuId, button.key(), "executor harus player/console: " + button.executor());
                if (button.javaMaterial() != null && Material.matchMaterial(button.javaMaterial()) == null)
                    warn(menuId, button.key(), "java-material tidak valid: " + button.javaMaterial());
            }
        }
    }

    private void warn(String menu, String button, String reason) {
        plugin.getLogger().warning("Menu config [" + menu + "/" + button + "]: " + reason);
    }

    public boolean commandAvailable(String template) {
        String root = rootCommand(template);
        return !root.isBlank() && plugin.getServer().getCommandMap().getCommand(root.toLowerCase(Locale.ROOT)) != null;
    }

    public String rootCommand(String template) {
        if (template == null || template.isBlank()) return "";
        String normalized = template.trim();
        if (normalized.startsWith("/")) normalized = normalized.substring(1);
        int space = normalized.indexOf(' ');
        String root = space < 0 ? normalized : normalized.substring(0, space);
        return root.contains("%") ? "" : root;
    }

    public MenuButton findButton(MenuDefinition menu, String key) {
        if (key == null) return null;
        for (MenuButton button : menu.buttons()) if (button.key().equals(key)) return button;
        return null;
    }

    public String normalizeMenuId(String menuId) {
        if (menuId == null || menuId.isBlank()) return "main";
        return menuId.trim().toLowerCase(Locale.ROOT);
    }

    public record Availability(boolean available, String code, String detail) { }
    public record MenuDefinition(String id, String title, String content, String backMenu, List<MenuButton> buttons) { }
    public record MenuButton(String key, String name, String type, String command, String executor,
                             String submenu, String icon, String javaMaterial, String permission, int order,
                             List<String> lore, List<String> requiredPlugins, String requiredCommand,
                             boolean autoDetectCommand) { }
}
'''

REPORT_184 = r'''package id.cadera.memberbook.report;

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
'''

ADMIN_184 = r'''package id.cadera.memberbook.command;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.item.MemberBookService;
import id.cadera.memberbook.menu.MenuConfigService;
import id.cadera.memberbook.report.ReportService;
import id.cadera.memberbook.util.Colors;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class MemberBookAdminCommand implements CommandExecutor, TabCompleter {
    private static final String PERMISSION = "cdrmemberbook.admin.memberbook";
    private final CdrMemberBookPlugin plugin;

    public MemberBookAdminCommand(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (!sender.hasPermission(PERMISSION)) {
            sender.sendMessage(Colors.legacy("&cKamu tidak punya izin untuk command ini."));
            return true;
        }
        if (args.length == 0) { sendUsage(sender, label); return true; }
        String action = args[0].toLowerCase(Locale.ROOT);
        if (action.equals("reports")) { handleReports(sender, args); return true; }
        if (action.equals("report")) { handleReport(sender, args); return true; }
        if (args.length < 2) { sendUsage(sender, label); return true; }

        Player target = Bukkit.getPlayerExact(args[1]);
        if (target == null) {
            sender.sendMessage(Colors.legacy("&cPlayer &f" + args[1] + " &ctidak ditemukan atau sedang offline."));
            return true;
        }
        MemberBookService service = plugin.memberBook();
        switch (action) {
            case "give" -> {
                if (!service.isEligibleForBook(target)) { sender.sendMessage(Colors.legacy("&e" + target.getName() + " &cbukan player yang eligible menerima Member Book.")); return true; }
                boolean success = service.forceGive(target);
                sender.sendMessage(Colors.legacy(success ? "&aMember Book dipastikan tersedia untuk &f" + target.getName() + "&a."
                        : "&eInventory/cursor &f" + target.getName() + " &epenuh."));
            }
            case "remove" -> {
                int removed = service.forceRemove(target);
                sender.sendMessage(Colors.legacy("&aMenghapus &f" + removed + " &acopy Member Book dari &f" + target.getName() + "&a."));
            }
            case "fix" -> {
                if (!service.isEligibleForBook(target)) { sender.sendMessage(Colors.legacy("&e" + target.getName() + " &cbukan player yang eligible menerima Member Book.")); return true; }
                sender.sendMessage(Colors.legacy(service.forceRepair(target)
                        ? "&aMember Book &f" + target.getName() + " &aberhasil diperiksa dan diperbaiki."
                        : "&eRecovery belum bisa menaruh buku karena inventory/cursor penuh."));
            }
            case "refresh" -> sender.sendMessage(Colors.legacy(service.refreshDynamicBook(target)
                    ? "&aDynamic Member Book &f" + target.getName() + " &aberhasil direfresh."
                    : "&eTidak ada Member Book aktif yang bisa direfresh."));
            case "status" -> sendStatus(sender, target, service.inspect(target));
            case "menudebug" -> sendMenuDebug(sender, target, args.length >= 3 ? args[2] : "main");
            case "tutorialreset" -> {
                plugin.tutorial().reset(target);
                sender.sendMessage(Colors.legacy("&aFirst Join Tutorial di-reset untuk &f" + target.getName() + "&a."));
            }
            case "tutorialshow" -> {
                if (!plugin.tutorial().canShow(target)) { sender.sendMessage(Colors.legacy("&eTutorial hanya bisa ditampilkan ke player yang eligible.")); return true; }
                plugin.tutorial().showNow(target);
                sender.sendMessage(Colors.legacy("&aTutorial ditampilkan ke &f" + target.getName() + "&a."));
            }
            default -> sendUsage(sender, label);
        }
        return true;
    }

    private void sendStatus(CommandSender sender, Player target, MemberBookService.BookStatus status) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook Status &8- &f" + target.getName()));
        sender.sendMessage(Colors.legacy("&7Mode: &f" + status.mode() + (status.configuredModeValid() ? "" : " &c(config invalid -> fallback)")));
        sender.sendMessage(Colors.legacy("&7Platform: &f" + (status.bedrock() ? "Bedrock" : "Java") + " &8| &7Eligible: &f" + status.eligible()));
        sender.sendMessage(Colors.legacy("&7Copies: &f" + status.visibleCopies() + " &8(inv=" + status.inventoryCopies() + ", cursor=" + status.cursorBook() + ", external=" + status.externalCopies() + ")"));
        sender.sendMessage(Colors.legacy("&7Reserved slot: &f" + status.reservedSlot() + " &8| &7Book in slot: &f" + status.bookInReservedSlot()));
        sender.sendMessage(Colors.legacy("&7Recovery: &f" + status.recoveryEnabled() + " &8| &7Suppressed: &f" + status.recoverySuppressed() + " &8| &7Fixed return pending: &f" + status.fixedReturnPending()));
        sender.sendMessage(Colors.legacy("&7External protection: &f" + status.externalStorageProtected() + " &8| &7Drop protection: &f" + status.dropProtected() + " &8| &7Dynamic: &f" + status.dynamicEnabled()));
    }

    private void sendMenuDebug(CommandSender sender, Player target, String menuId) {
        MenuConfigService.MenuDefinition menu = plugin.menus().getMenu(menuId);
        if (menu == null) { sender.sendMessage(Colors.legacy("&cMenu tidak ditemukan: &f" + menuId)); return; }
        boolean hidePerm = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);
        sender.sendMessage(Colors.legacy("&dMenu Debug &8- &f" + target.getName() + " &8/ &f" + menu.id()));
        for (MenuConfigService.MenuButton button : menu.buttons()) {
            boolean permission = plugin.menus().canUse(target, button);
            MenuConfigService.Availability available = plugin.menus().availability(target, button);
            boolean visible = (!hidePerm || permission) && (!hideUnavailable || available.available());
            sender.sendMessage(Colors.legacy((visible ? "&a✔ " : "&c✘ ") + "&f" + button.key()
                    + " &8| &7type=&f" + button.type() + " &8| &7perm=&f" + permission
                    + " &8| &7availability=&f" + available.code() + (available.detail().isBlank() ? "" : " &8(" + available.detail() + ")")));
        }
    }

    private void handleReports(CommandSender sender, String[] args) {
        int page = 1;
        if (args.length >= 2) try { page = Math.max(1, Integer.parseInt(args[1])); } catch (NumberFormatException ignored) { }
        ReportService.Status filter = null;
        if (args.length >= 3 && !args[2].equalsIgnoreCase("all")) {
            try { filter = ReportService.Status.valueOf(args[2].toUpperCase(Locale.ROOT)); }
            catch (IllegalArgumentException ex) { sender.sendMessage(Colors.legacy("&cStatus harus open/resolved/all.")); return; }
        }
        List<ReportService.ReportEntry> entries = plugin.reports().list(filter);
        int size = Math.max(1, plugin.getConfig().getInt("integrations.report.admin-page-size", 8));
        int pages = Math.max(1, (entries.size() + size - 1) / size);
        page = Math.min(page, pages);
        int start = (page - 1) * size;
        int end = Math.min(entries.size(), start + size);
        sender.sendMessage(Colors.legacy("&dCdrMemberBook Reports &8- &f" + page + "/" + pages + " &8| &7total=&f" + entries.size()
                + " &8| &7open=&f" + plugin.reports().count(ReportService.Status.OPEN)));
        if (entries.isEmpty()) { sender.sendMessage(Colors.legacy("&7Tidak ada report.")); return; }
        for (int i = start; i < end; i++) {
            ReportService.ReportEntry e = entries.get(i);
            sender.sendMessage(Colors.legacy((e.status() == ReportService.Status.OPEN ? "&c" : "&a") + "#" + e.id()
                    + " &f" + e.reporterName() + " &8-> &f" + e.targetName() + " &8| &7" + shorten(e.reason(), 48)));
        }
    }

    private void handleReport(CommandSender sender, String[] args) {
        if (args.length < 3) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook report <view|resolve|reopen|delete> <id>")); return; }
        int id;
        try { id = Integer.parseInt(args[2]); } catch (NumberFormatException ex) { sender.sendMessage(Colors.legacy("&cID report tidak valid.")); return; }
        String action = args[1].toLowerCase(Locale.ROOT);
        ReportService.ReportEntry e = plugin.reports().get(id);
        if (e == null) { sender.sendMessage(Colors.legacy("&cReport #" + id + " tidak ditemukan.")); return; }
        String staff = sender.getName();
        switch (action) {
            case "view" -> {
                sender.sendMessage(Colors.legacy("&dReport #" + e.id() + " &8- &f" + e.status()));
                sender.sendMessage(Colors.legacy("&7Reporter: &f" + e.reporterName() + " &8(" + e.reporterUuid() + ")"));
                sender.sendMessage(Colors.legacy("&7Target: &f" + e.targetName() + " &8(" + e.targetUuid() + ")"));
                sender.sendMessage(Colors.legacy("&7Alasan: &f" + e.reason()));
                sender.sendMessage(Colors.legacy("&7Waktu: &f" + e.createdAt() + " &8| &7Lokasi: &f" + e.world() + " " + e.x() + "," + e.y() + "," + e.z()));
                if (e.status() == ReportService.Status.RESOLVED) sender.sendMessage(Colors.legacy("&7Resolved: &f" + e.resolvedBy() + " &8@ &f" + e.resolvedAt()));
            }
            case "resolve" -> { plugin.reports().resolve(id, staff); sender.sendMessage(Colors.legacy("&aReport #" + id + " ditandai RESOLVED.")); }
            case "reopen" -> { plugin.reports().reopen(id, staff); sender.sendMessage(Colors.legacy("&eReport #" + id + " dibuka kembali.")); }
            case "delete" -> { plugin.reports().delete(id); sender.sendMessage(Colors.legacy("&aReport #" + id + " dihapus.")); }
            default -> sender.sendMessage(Colors.legacy("&cAction report harus view/resolve/reopen/delete."));
        }
    }

    private String shorten(String value, int max) { return value.length() <= max ? value : value.substring(0, max - 3) + "..."; }

    private void sendUsage(CommandSender sender, String label) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook &fv1.8.4 &8- &7Admin Tools"));
        sender.sendMessage(Colors.legacy("&f/" + label + " <give|remove|fix|refresh|status|tutorialreset|tutorialshow> <player>"));
        sender.sendMessage(Colors.legacy("&f/" + label + " menudebug <player> [menu] &8- &7cek alasan tombol tampil/hilang"));
        sender.sendMessage(Colors.legacy("&f/" + label + " reports [page] [open|resolved|all] &8- &7list report"));
        sender.sendMessage(Colors.legacy("&f/" + label + " report <view|resolve|reopen|delete> <id>"));
    }

    @Override
    public @Nullable List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                                 @NotNull String alias, @NotNull String[] args) {
        if (!sender.hasPermission(PERMISSION)) return List.of();
        if (args.length == 1) {
            String p = args[0].toLowerCase(Locale.ROOT);
            return List.of("give","remove","fix","refresh","status","menudebug","tutorialreset","tutorialshow","reports","report")
                    .stream().filter(v -> v.startsWith(p)).toList();
        }
        if (args[0].equalsIgnoreCase("report")) {
            if (args.length == 2) return List.of("view","resolve","reopen","delete").stream().filter(v -> v.startsWith(args[1].toLowerCase(Locale.ROOT))).toList();
            return List.of();
        }
        if (args[0].equalsIgnoreCase("reports")) {
            if (args.length == 3) return List.of("open","resolved","all").stream().filter(v -> v.startsWith(args[2].toLowerCase(Locale.ROOT))).toList();
            return List.of();
        }
        if (args.length == 2) {
            String p = args[1].toLowerCase(Locale.ROOT);
            return Bukkit.getOnlinePlayers().stream().map(Player::getName).filter(n -> n.toLowerCase(Locale.ROOT).startsWith(p)).sorted(String.CASE_INSENSITIVE_ORDER).toList();
        }
        if (args[0].equalsIgnoreCase("menudebug") && args.length == 3) {
            List<String> ids = new ArrayList<>(); ids.add("main");
            var sec = plugin.getConfig().getConfigurationSection("menu.submenus"); if (sec != null) ids.addAll(sec.getKeys(false));
            String p=args[2].toLowerCase(Locale.ROOT); return ids.stream().filter(v -> v.toLowerCase(Locale.ROOT).startsWith(p)).sorted().toList();
        }
        return List.of();
    }
}
'''

ACTION_SERVICE = r'''package id.cadera.memberbook.menu;

import id.cadera.memberbook.CdrMemberBookPlugin;
import org.bukkit.Sound;
import org.bukkit.entity.Player;

import java.util.List;
import java.util.Locale;

public final class MenuActionService {
    private final CdrMemberBookPlugin plugin;
    public MenuActionService(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    public void execute(Player player, List<MenuConfigService.MenuAction> actions) {
        if (actions == null || actions.isEmpty()) return;
        run(player, actions, 0);
    }

    private void run(Player player, List<MenuConfigService.MenuAction> actions, int index) {
        if (!player.isOnline() || index >= actions.size()) return;
        MenuConfigService.MenuAction action = actions.get(index);
        String type = action.type().toLowerCase(Locale.ROOT);
        try {
            switch (type) {
                case "delay" -> {
                    long ticks = Math.max(1L, action.ticks());
                    plugin.getServer().getScheduler().runTaskLater(plugin, () -> run(player, actions, index + 1), ticks);
                    return;
                }
                case "command" -> plugin.dispatchActionCommand(player, action.value(), action.executor());
                case "console-command" -> plugin.dispatchActionCommand(player, action.value(), "console");
                case "message" -> player.sendMessage(plugin.formatMenuText(action.value(), player));
                case "sound" -> {
                    Sound sound = Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT));
                    player.playSound(player.getLocation(), sound, action.volume(), action.pitch());
                }
                case "close" -> player.closeInventory();
                case "open-menu" -> plugin.openMenu(player, action.value());
                default -> plugin.getLogger().warning("Unknown menu action type: " + action.type());
            }
        } catch (Throwable throwable) {
            plugin.getLogger().warning("Menu action failed [" + action.type() + "]: " + throwable.getMessage());
        }
        run(player, actions, index + 1);
    }
}
'''

MENU_190 = r'''package id.cadera.memberbook.menu;

import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import id.cadera.memberbook.CdrMemberBookPlugin;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class MenuConfigService {
    private static final Set<String> KNOWN_TYPES = Set.of("command", "teleport", "homes", "pay", "trade", "report", "submenu", "close");
    private static final Set<String> ACTION_TYPES = Set.of("command", "console-command", "message", "sound", "close", "open-menu", "delay");
    private final CdrMemberBookPlugin plugin;
    public MenuConfigService(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    public MenuDefinition getMenu(String menuId) {
        String normalized = normalizeMenuId(menuId);
        String path = normalized.equals("main") ? "menu.main" : "menu.submenus." + normalized;
        ConfigurationSection section = plugin.getConfig().getConfigurationSection(path);
        if (section == null) return null;
        String title = section.getString("title", normalized.equals("main") ? "CdrMemberBook • Menu Member" : normalized);
        String content = section.getString("content", "");
        String backMenu = normalizeMenuId(section.getString("back-menu", "main"));
        List<MenuButton> buttons = new ArrayList<>();
        ConfigurationSection bs = section.getConfigurationSection("buttons");
        if (bs != null) for (String key : bs.getKeys(false)) {
            ConfigurationSection b = bs.getConfigurationSection(key);
            if (b == null || !b.getBoolean("enabled", true)) continue;
            String type = b.getString("type", "command"); if (type == null) type = "command";
            buttons.add(new MenuButton(key, b.getString("name", key), type.trim().toLowerCase(Locale.ROOT),
                    b.getString("command", ""), b.getString("executor", "player"), b.getString("submenu", ""),
                    b.getString("icon", ""), b.getString("java-material", "PAPER"), b.getString("permission", ""),
                    b.getInt("order", 100), b.getStringList("lore"), b.getStringList("requires-plugins"),
                    b.getString("requires-command", ""), b.getBoolean("auto-detect-command", true), parseActions(b)));
        }
        buttons.sort(Comparator.comparingInt(MenuButton::order).thenComparing(MenuButton::key));
        return new MenuDefinition(normalized, title == null ? "" : title, content == null ? "" : content, backMenu, List.copyOf(buttons));
    }

    private List<MenuAction> parseActions(ConfigurationSection button) {
        List<MenuAction> actions = new ArrayList<>();
        for (Map<?, ?> raw : button.getMapList("actions")) {
            String type = string(raw.get("type"), "").trim().toLowerCase(Locale.ROOT);
            if (type.isBlank()) continue;
            String value = string(raw.get("value"), "");
            if (value.isBlank()) {
                for (String key : List.of("command", "message", "sound", "menu")) if (raw.get(key) != null) { value = raw.get(key).toString(); break; }
            }
            actions.add(new MenuAction(type, value, string(raw.get("executor"), "player"), number(raw.get("ticks"), 1L),
                    decimal(raw.get("volume"), 1.0f), decimal(raw.get("pitch"), 1.0f)));
        }
        return List.copyOf(actions);
    }
    private String string(Object value, String fallback) { return value == null ? fallback : value.toString(); }
    private long number(Object value, long fallback) { try { return value == null ? fallback : Long.parseLong(value.toString()); } catch (NumberFormatException e) { return fallback; } }
    private float decimal(Object value, float fallback) { try { return value == null ? fallback : Float.parseFloat(value.toString()); } catch (NumberFormatException e) { return fallback; } }

    public List<MenuButton> visibleButtons(MenuDefinition menu, Player player) {
        boolean hidePerm = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);
        return menu.buttons().stream().filter(b -> !hidePerm || canUse(player,b)).filter(b -> !hideUnavailable || availability(player,b).available()).toList();
    }
    public boolean canUse(Player player, MenuButton button) { String p=button.permission(); return p==null || p.isBlank() || player.hasPermission(p); }
    public boolean isAvailable(Player player, MenuButton button) { return availability(player,button).available(); }

    public Availability availability(Player player, MenuButton button) {
        for (String p : button.requiredPlugins()) if (p != null && !p.isBlank() && !plugin.getServer().getPluginManager().isPluginEnabled(p.trim())) return new Availability(false,"missing-plugin",p.trim());
        if (button.requiredCommand()!=null && !button.requiredCommand().isBlank() && !commandAvailable(button.requiredCommand())) return new Availability(false,"missing-command",rootCommand(button.requiredCommand()));
        if (!button.actions().isEmpty()) return actionsAvailability(button.actions());
        if (!KNOWN_TYPES.contains(button.type())) return new Availability(false,"invalid-type","type="+button.type());
        return switch(button.type()) {
            case "teleport","close" -> new Availability(true,"ok","built-in");
            case "submenu" -> button.submenu()==null || button.submenu().isBlank() || getMenu(button.submenu())==null ? new Availability(false,"missing-submenu",button.submenu()==null?"":button.submenu()) : new Availability(true,"ok","submenu="+button.submenu());
            case "homes" -> plugin.homes()!=null && plugin.homes().available() ? new Availability(true,"ok","EssentialsX") : new Availability(false,"missing-integration","EssentialsX Home");
            case "pay" -> availableCommand(plugin.getConfig().getString("integrations.pay.command","pay %target% %amount%"));
            case "trade" -> !plugin.getServer().getPluginManager().isPluginEnabled("AxTrade") ? new Availability(false,"missing-plugin","AxTrade") : availableCommand(plugin.getConfig().getString("integrations.axtrade.send-command","axtrade %target%"));
            case "report" -> (plugin.reports()!=null && plugin.reports().enabled() && plugin.forms()!=null && plugin.forms().isBedrock(player)) ? new Availability(true,"ok","native-report") : availableCommand(button.command());
            case "command" -> button.command()==null || button.command().isBlank() ? new Availability(false,"empty-command","command kosong") : (!plugin.getConfig().getBoolean("menu.auto-detect-command-dependencies",true) || !button.autoDetectCommand() ? new Availability(true,"ok","auto-detect off") : availableCommand(button.command()));
            default -> new Availability(false,"invalid-type",button.type());
        };
    }

    private Availability actionsAvailability(List<MenuAction> actions) {
        for (MenuAction action : actions) {
            if (!ACTION_TYPES.contains(action.type())) return new Availability(false,"invalid-action","action="+action.type());
            if ((action.type().equals("command") || action.type().equals("console-command")) && plugin.getConfig().getBoolean("menu.auto-detect-command-dependencies",true) && !commandAvailable(action.value())) return new Availability(false,"missing-command",rootCommand(action.value()));
            if (action.type().equals("open-menu") && getMenu(action.value()) == null) return new Availability(false,"missing-submenu",action.value());
            if (action.type().equals("sound")) try { org.bukkit.Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT)); } catch (Exception e) { return new Availability(false,"invalid-sound",action.value()); }
        }
        return new Availability(true,"ok","actions="+actions.size());
    }
    private Availability availableCommand(String c) { return commandAvailable(c) ? new Availability(true,"ok","command="+rootCommand(c)) : new Availability(false,"missing-command",rootCommand(c)); }

    public void validateConfiguration() {
        if (!plugin.getConfig().getBoolean("menu.log-invalid-buttons",true)) return;
        List<String> ids=new ArrayList<>(); ids.add("main"); ConfigurationSection sec=plugin.getConfig().getConfigurationSection("menu.submenus"); if(sec!=null) ids.addAll(sec.getKeys(false));
        for(String id:ids){ MenuDefinition menu=getMenu(id); if(menu==null)continue; for(MenuButton b:menu.buttons()){
            if(b.actions().isEmpty() && !KNOWN_TYPES.contains(b.type())) warn(id,b.key(),"type tidak dikenal: "+b.type());
            if(b.actions().isEmpty() && b.type().equals("command") && (b.command()==null||b.command().isBlank())) warn(id,b.key(),"command kosong");
            if(b.javaMaterial()!=null && Material.matchMaterial(b.javaMaterial())==null) warn(id,b.key(),"java-material tidak valid: "+b.javaMaterial());
            for(MenuAction a:b.actions()) if(!ACTION_TYPES.contains(a.type())) warn(id,b.key(),"action tidak dikenal: "+a.type());
        }}
    }
    private void warn(String m,String b,String r){ plugin.getLogger().warning("Menu config ["+m+"/"+b+"]: "+r); }
    public boolean commandAvailable(String template){String r=rootCommand(template);return !r.isBlank()&&plugin.getServer().getCommandMap().getCommand(r.toLowerCase(Locale.ROOT))!=null;}
    public String rootCommand(String template){if(template==null||template.isBlank())return"";String n=template.trim();if(n.startsWith("/"))n=n.substring(1);int sp=n.indexOf(' ');String r=sp<0?n:n.substring(0,sp);return r.contains("%")?"":r;}
    public MenuButton findButton(MenuDefinition m,String k){if(k==null)return null;for(MenuButton b:m.buttons())if(b.key().equals(k))return b;return null;}
    public String normalizeMenuId(String id){return id==null||id.isBlank()?"main":id.trim().toLowerCase(Locale.ROOT);}

    public record Availability(boolean available,String code,String detail){}
    public record MenuAction(String type,String value,String executor,long ticks,float volume,float pitch){}
    public record MenuDefinition(String id,String title,String content,String backMenu,List<MenuButton> buttons){}
    public record MenuButton(String key,String name,String type,String command,String executor,String submenu,String icon,String javaMaterial,String permission,int order,List<String> lore,List<String> requiredPlugins,String requiredCommand,boolean autoDetectCommand,List<MenuAction> actions){}
}
'''

MENU_191 = MENU_190.replace('import java.util.Set;\n', 'import java.util.Set;\nimport me.clip.placeholderapi.PlaceholderAPI;\n')
MENU_191 = MENU_191.replace('b.getString("requires-command", ""), b.getBoolean("auto-detect-command", true), parseActions(b)));',
'''b.getString("requires-command", ""), b.getBoolean("auto-detect-command", true), parseActions(b), parseConditions(b)));''')
MENU_191 = MENU_191.replace('    private List<MenuAction> parseActions(ConfigurationSection button) {', r'''    private MenuConditions parseConditions(ConfigurationSection button) {
        ConfigurationSection c = button.getConfigurationSection("conditions");
        if (c == null) return new MenuConditions("ANY", List.of(), List.of(), List.of(), 0, -1, List.of());
        List<PlaceholderCondition> placeholders = new ArrayList<>();
        for (Map<?, ?> raw : c.getMapList("placeholders")) {
            placeholders.add(new PlaceholderCondition(string(raw.get("value"), ""), string(raw.get("operator"), "=="), string(raw.get("compare"), "")));
        }
        ConfigurationSection single = c.getConfigurationSection("placeholder");
        if (single != null) placeholders.add(new PlaceholderCondition(single.getString("value", ""), single.getString("operator", "=="), single.getString("compare", "")));
        return new MenuConditions(c.getString("platform", "ANY"), c.getStringList("worlds"), c.getStringList("excluded-worlds"),
                c.getStringList("permissions"), c.getInt("min-online", 0), c.getInt("max-online", -1), List.copyOf(placeholders));
    }

    private List<MenuAction> parseActions(ConfigurationSection button) {''')
MENU_191 = MENU_191.replace('        if (!button.actions().isEmpty()) return actionsAvailability(button.actions());',
'''        Availability condition = conditionsAvailability(player, button.conditions());
        if (!condition.available()) return condition;
        if (!button.actions().isEmpty()) return actionsAvailability(button.actions());''')
insert_conditions = r'''
    private Availability conditionsAvailability(Player player, MenuConditions c) {
        if (c == null) return new Availability(true,"ok","no-conditions");
        for (String permission : c.permissions()) if (permission != null && !permission.isBlank() && !player.hasPermission(permission)) return new Availability(false,"condition-permission",permission);
        String platform = c.platform() == null ? "ANY" : c.platform().trim().toUpperCase(Locale.ROOT);
        boolean bedrock = plugin.forms()!=null && plugin.forms().isBedrock(player);
        if (platform.equals("BEDROCK") && !bedrock) return new Availability(false,"condition-platform","BEDROCK");
        if (platform.equals("JAVA") && bedrock) return new Availability(false,"condition-platform","JAVA");
        if (!Set.of("ANY","JAVA","BEDROCK").contains(platform)) return new Availability(false,"condition-platform-invalid",platform);
        if (!c.worlds().isEmpty() && c.worlds().stream().noneMatch(w -> w.equalsIgnoreCase(player.getWorld().getName()))) return new Availability(false,"condition-world",player.getWorld().getName());
        if (c.excludedWorlds().stream().anyMatch(w -> w.equalsIgnoreCase(player.getWorld().getName()))) return new Availability(false,"condition-world-excluded",player.getWorld().getName());
        int online = plugin.getServer().getOnlinePlayers().size();
        if (online < c.minOnline()) return new Availability(false,"condition-online","min="+c.minOnline());
        if (c.maxOnline() >= 0 && online > c.maxOnline()) return new Availability(false,"condition-online","max="+c.maxOnline());
        if (!c.placeholders().isEmpty() && !plugin.getServer().getPluginManager().isPluginEnabled("PlaceholderAPI")) return new Availability(false,"condition-placeholderapi","PlaceholderAPI missing");
        for (PlaceholderCondition p : c.placeholders()) {
            String left = resolveConditionText(player, p.value());
            String right = resolveConditionText(player, p.compare());
            if (!compare(left, p.operator(), right)) return new Availability(false,"condition-placeholder",p.value()+" "+p.operator()+" "+p.compare()+" (got="+left+")");
        }
        return new Availability(true,"ok","conditions-pass");
    }

    private String resolveConditionText(Player player, String value) {
        String text = value == null ? "" : value.replace("%player%", player.getName()).replace("%uuid%", player.getUniqueId().toString()).replace("%world%", player.getWorld().getName()).replace("%online%", Integer.toString(plugin.getServer().getOnlinePlayers().size()));
        if (plugin.getServer().getPluginManager().isPluginEnabled("PlaceholderAPI") && plugin.getConfig().getBoolean("menu.conditions.placeholderapi", true)) {
            try { text = PlaceholderAPI.setPlaceholders(player, text); } catch (Throwable ignored) { }
        }
        return text;
    }

    private boolean compare(String left, String operator, String right) {
        String op = operator == null ? "==" : operator.trim().toLowerCase(Locale.ROOT);
        return switch (op) {
            case "==", "=", "equals" -> left.equalsIgnoreCase(right);
            case "!=", "not_equals" -> !left.equalsIgnoreCase(right);
            case "contains" -> left.toLowerCase(Locale.ROOT).contains(right.toLowerCase(Locale.ROOT));
            case "not_contains" -> !left.toLowerCase(Locale.ROOT).contains(right.toLowerCase(Locale.ROOT));
            case "starts_with" -> left.toLowerCase(Locale.ROOT).startsWith(right.toLowerCase(Locale.ROOT));
            case "ends_with" -> left.toLowerCase(Locale.ROOT).endsWith(right.toLowerCase(Locale.ROOT));
            case ">", ">=", "<", "<=" -> numericCompare(left, op, right);
            default -> false;
        };
    }
    private boolean numericCompare(String left, String op, String right) {
        try { double a=Double.parseDouble(left.replace(",", "").trim()), b=Double.parseDouble(right.replace(",", "").trim()); return switch(op){case ">"->a>b;case ">="->a>=b;case "<"->a<b;case "<="->a<=b;default->false;}; }
        catch (NumberFormatException ignored) { return false; }
    }
'''
MENU_191 = MENU_191.replace('    private Availability actionsAvailability(List<MenuAction> actions) {', insert_conditions + '\n    private Availability actionsAvailability(List<MenuAction> actions) {')
MENU_191 = MENU_191.replace('public record MenuAction(String type,String value,String executor,long ticks,float volume,float pitch){}\n    public record MenuDefinition',
'''public record MenuAction(String type,String value,String executor,long ticks,float volume,float pitch){}
    public record PlaceholderCondition(String value,String operator,String compare){}
    public record MenuConditions(String platform,List<String> worlds,List<String> excludedWorlds,List<String> permissions,int minOnline,int maxOnline,List<PlaceholderCondition> placeholders){}
    public record MenuDefinition''')
MENU_191 = MENU_191.replace('String requiredCommand,boolean autoDetectCommand,List<MenuAction> actions){}',
'String requiredCommand,boolean autoDetectCommand,List<MenuAction> actions,MenuConditions conditions){}')


def stage_183():
    set_version('1.8.3', 15)
    write('src/main/java/id/cadera/memberbook/menu/MenuConfigService.java', MENU_183)
    p='src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'; s=read(p)
    s=replace_once(s, '            case "status" -> {\n', '''            case "menudebug" -> {\n                String menuId = args.length >= 3 ? args[2] : "main";\n                var menu = plugin.menus().getMenu(menuId);\n                if (menu == null) { sender.sendMessage(Colors.legacy("&cMenu tidak ditemukan: &f" + menuId)); break; }\n                boolean hidePerm = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);\n                boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);\n                sender.sendMessage(Colors.legacy("&dMenu Debug &8- &f" + target.getName() + " &8/ &f" + menu.id()));\n                for (var button : menu.buttons()) {\n                    boolean permission = plugin.menus().canUse(target, button);\n                    var available = plugin.menus().availability(target, button);\n                    boolean visible = (!hidePerm || permission) && (!hideUnavailable || available.available());\n                    sender.sendMessage(Colors.legacy((visible ? "&a✔ " : "&c✘ ") + "&f" + button.key() + " &8| &7type=&f" + button.type()\n                            + " &8| &7perm=&f" + permission + " &8| &7availability=&f" + available.code()\n                            + (available.detail().isBlank() ? "" : " &8(" + available.detail() + ")")));\n                }\n            }\n            case "status" -> {\n''', 'insert menudebug')
    s=s.replace('List.of("give", "remove", "fix", "refresh", "status", "tutorialreset", "tutorialshow")', 'List.of("give", "remove", "fix", "refresh", "status", "menudebug", "tutorialreset", "tutorialshow")')
    s=s.replace('&f/" + label + " status <player> &8- &7diagnostic Book Modes + recovery"));', '&f/" + label + " status <player> &8- &7diagnostic Book Modes + recovery"));\n        sender.sendMessage(Colors.legacy("&f/" + label + " menudebug <player> [menu] &8- &7cek tombol tampil/hilang"));')
    s=s.replace('&dCdrMemberBook &fv1.7.0', '&dCdrMemberBook &fv1.8.3')
    write(p,s)
    p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
    s=replace_once(s, '        memberBookService.validateConfiguration();\n', '        memberBookService.validateConfiguration();\n        menuConfigService.validateConfiguration();\n', 'enable menu validation')
    s=replace_once(s, '            memberBookService.validateConfiguration();\n            memberBookService.restartEnforcement();', '            memberBookService.validateConfiguration();\n            menuConfigService.validateConfiguration();\n            memberBookService.restartEnforcement();', 'reload menu validation')
    write(p,s)
    patch_main_migration('1.8.3',14,15,['getConfig().set("menu.log-invalid-buttons", true);'])
    cfg=read('src/main/resources/config.yml')
    cfg=replace_once(cfg,'  auto-detect-command-dependencies: true\n','  auto-detect-command-dependencies: true\n  # Warning startup/reload untuk type/material/submenu config yang salah.\n  log-invalid-buttons: true\n','config log invalid')
    write('src/main/resources/config.yml',cfg)
    add_changelog('1.8.3','Smart Menu Stability',['Added `/cdrmemberbook menudebug <player> [menu]` with explicit visibility/dependency reasons.','Added startup/reload menu configuration validation and warnings.','Dead buttons now expose structured availability codes for debugging.'])


def stage_184():
    set_version('1.8.4',16)
    write('src/main/java/id/cadera/memberbook/report/ReportService.java', REPORT_184)
    write('src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java', ADMIN_184)
    patch_main_migration('1.8.4',15,16,['getConfig().set("integrations.report.admin-page-size", 8);'])
    cfg=read('src/main/resources/config.yml')
    cfg=replace_once(cfg,'    max-reason-length: 200\n','    max-reason-length: 200\n    # Jumlah report per halaman untuk /cdrmemberbook reports.\n    admin-page-size: 8\n','report page size')
    write('src/main/resources/config.yml',cfg)
    add_changelog('1.8.4','Report Management',['Added report status lifecycle: OPEN/RESOLVED with resolver and timestamp.','Added admin list/view/resolve/reopen/delete commands.','Existing report files remain readable; entries without status are treated as OPEN.'])


def stage_190():
    set_version('1.9.0',17)
    write('src/main/java/id/cadera/memberbook/menu/MenuConfigService.java', MENU_190)
    write('src/main/java/id/cadera/memberbook/menu/MenuActionService.java', ACTION_SERVICE)
    p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
    s=replace_once(s,'import id.cadera.memberbook.menu.MenuConfigService;\n','import id.cadera.memberbook.menu.MenuConfigService;\nimport id.cadera.memberbook.menu.MenuActionService;\n','action import')
    s=replace_once(s,'    private MenuConfigService menuConfigService;\n','    private MenuConfigService menuConfigService;\n    private MenuActionService menuActionService;\n','action field')
    s=replace_once(s,'        menuConfigService = new MenuConfigService(this);\n','        menuConfigService = new MenuConfigService(this);\n        menuActionService = new MenuActionService(this);\n','action init')
    s=replace_once(s,'    public void openMenu(Player player) {\n        if (formService != null && formService.isBedrock(player)) {\n            formService.showMainMenu(player);\n        } else {\n            javaMenuService.showMain(player);\n        }\n    }\n', '''    public void openMenu(Player player) { openMenu(player, "main"); }\n\n    public void openMenu(Player player, String menuId) {\n        String id = menuId == null || menuId.isBlank() ? "main" : menuId;\n        if (formService != null && formService.isBedrock(player)) formService.showConfiguredMenu(player, id);\n        else javaMenuService.showConfiguredMenu(player, id, 0);\n    }\n''','openMenu overload')
    s=replace_once(s,'    public MenuConfigService menus() {\n        return menuConfigService;\n    }\n','    public MenuConfigService menus() {\n        return menuConfigService;\n    }\n\n    public MenuActionService menuActions() { return menuActionService; }\n','action accessor')
    s=replace_once(s,'    public void dispatchPlayerTemplate(Player player, String template, Map<String, String> placeholders) {','    public void dispatchActionCommand(Player player, String template, String executor) {\n        if (template == null || template.isBlank()) { message(player, "action-disabled"); return; }\n        String command = template.replace("%player%", player.getName()).replace("%uuid%", player.getUniqueId().toString()).replace("%world%", player.getWorld().getName());\n        dispatchCommand(player, command, executor);\n    }\n\n    public void dispatchPlayerTemplate(Player player, String template, Map<String, String> placeholders) {','dispatch action')
    write(p,s)
    for pth in ['src/main/java/id/cadera/memberbook/form/BedrockFormService.java','src/main/java/id/cadera/memberbook/gui/JavaMenuService.java']:
        s=read(pth)
        marker='        switch (button.type().toLowerCase(Locale.ROOT)) {'
        inject='''        if (button.actions() != null && !button.actions().isEmpty()) {\n            plugin.menuActions().execute(player, button.actions());\n            return;\n        }\n\n'''+marker
        s=replace_once(s,marker,inject,pth+' action handler')
        write(pth,s)
    patch_main_migration('1.9.0',16,17,['getConfig().set("menu.actions.enabled", true);'])
    cfg=read('src/main/resources/config.yml')
    cfg=replace_once(cfg,'  log-invalid-buttons: true\n','  log-invalid-buttons: true\n  actions:\n    enabled: true\n','menu action enable')
    cfg=cfg.replace('#   close    = close the menu\n','#   close    = close the menu\n# Advanced actions v1.9.0: optional `actions:` list overrides legacy single action.\n# Types: command, console-command, message, sound, close, open-menu, delay.\n')
    write('src/main/resources/config.yml',cfg)
    add_changelog('1.9.0','Advanced Menu Actions',['Buttons can execute ordered action chains instead of one command.','Action types: command, console-command, message, sound, close, open-menu and delay.','Action chains keep legacy single-command buttons fully compatible.'])


def stage_191():
    set_version('1.9.1',18)
    write('src/main/java/id/cadera/memberbook/menu/MenuConfigService.java', MENU_191)
    patch_main_migration('1.9.1',17,18,['getConfig().set("menu.conditions.placeholderapi", true);'])
    cfg=read('src/main/resources/config.yml')
    cfg=replace_once(cfg,'  actions:\n    enabled: true\n','  actions:\n    enabled: true\n  conditions:\n    # Izinkan PlaceholderAPI untuk evaluasi conditions.placeholder(s).\n    placeholderapi: true\n','condition config')
    cfg=cfg.replace('# Types: command, console-command, message, sound, close, open-menu, delay.\n','# Types: command, console-command, message, sound, close, open-menu, delay.\n# Conditions v1.9.1: platform ANY/JAVA/BEDROCK, worlds, excluded-worlds, permissions,\n# min-online/max-online, dan placeholder comparisons (==, !=, contains, >, >=, <, <=).\n')
    write('src/main/resources/config.yml',cfg)
    p='src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'; s=read(p).replace('&dCdrMemberBook &fv1.8.4','&dCdrMemberBook &fv1.9.1'); write(p,s)
    add_changelog('1.9.1','Menu Conditions Advanced',['Added per-button platform, world, extra permission and online-count conditions.','Added PlaceholderAPI comparisons for rank/economy/level/custom plugin state.','Menu debug reports the exact condition that hides an unavailable button.'])
    rd=read('README.md')
    if '## Advanced Menu Actions & Conditions' not in rd:
        rd += r'''

## Advanced Menu Actions & Conditions

`v1.9.0` adds ordered button action chains (`command`, `console-command`, `message`, `sound`, `close`, `open-menu`, `delay`). `v1.9.1` adds smart conditions by platform, world, permission, online count and PlaceholderAPI comparisons. Use `/cdrmemberbook menudebug <player> [menu]` to see why each button is visible or hidden.

```yaml
example:
  enabled: true
  name: Ranked Shop
  type: command
  order: 200
  actions:
    - type: close
    - type: sound
      value: ENTITY_PLAYER_LEVELUP
    - type: command
      value: shop
    - type: message
      value: '&aShop dibuka.'
  conditions:
    platform: ANY
    worlds: [world]
    permissions: [server.shop]
    min-online: 1
    placeholders:
      - value: '%luckperms_primary_group%'
        operator: '!='
        compare: 'default'
```
'''
    write('README.md',rd)


if stage == '1.8.3': stage_183()
elif stage == '1.8.4': stage_184()
elif stage == '1.9.0': stage_190()
elif stage == '1.9.1': stage_191()
else: raise SystemExit('unknown stage '+stage)
print('applied',stage)
