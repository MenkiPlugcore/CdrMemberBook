package id.cadera.memberbook.menu;

import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import id.cadera.memberbook.CdrMemberBookPlugin;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

public final class MenuConfigService {
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
                ? "MOONSIGN • Menu Member"
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
                        button.getStringList("lore")
                ));
            }
        }

        buttons.sort(Comparator.comparingInt(MenuButton::order).thenComparing(MenuButton::key));
        return new MenuDefinition(normalized, title == null ? "" : title,
                content == null ? "" : content, backMenu, List.copyOf(buttons));
    }

    public List<MenuButton> visibleButtons(MenuDefinition menu, Player player) {
        boolean hideWithoutPermission = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        if (!hideWithoutPermission) return menu.buttons();
        return menu.buttons().stream().filter(button -> canUse(player, button)).toList();
    }

    public boolean canUse(Player player, MenuButton button) {
        String permission = button.permission();
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }

    public MenuButton findButton(MenuDefinition menu, String key) {
        if (key == null) return null;
        for (MenuButton button : menu.buttons()) {
            if (button.key().equals(key)) return button;
        }
        return null;
    }

    public String normalizeMenuId(String menuId) {
        if (menuId == null || menuId.isBlank()) return "main";
        return menuId.trim().toLowerCase(Locale.ROOT);
    }

    public record MenuDefinition(
            String id,
            String title,
            String content,
            String backMenu,
            List<MenuButton> buttons
    ) {}

    public record MenuButton(
            String key,
            String name,
            String type,
            String command,
            String executor,
            String submenu,
            String icon,
            String javaMaterial,
            String permission,
            int order,
            List<String> lore
    ) {}
}
