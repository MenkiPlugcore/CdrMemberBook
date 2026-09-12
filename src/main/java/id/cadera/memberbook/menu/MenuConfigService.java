package id.cadera.memberbook.menu;

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
