package id.cadera.memberbook.preference;

import id.cadera.memberbook.CdrMemberBookPlugin;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

public final class PreferenceService {
    public enum MenuMode { FULL, COMPACT }

    private final CdrMemberBookPlugin plugin;
    private final File file;
    private YamlConfiguration data;

    public PreferenceService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.file = new File(plugin.getDataFolder(), "preferences.yml");
        this.data = YamlConfiguration.loadConfiguration(file);
    }

    public boolean enabled() { return plugin.getConfig().getBoolean("preferences.enabled", true); }

    public boolean soundsEnabled(Player player) { return bool(player, "sounds", "preferences.defaults.sounds", true); }
    public boolean tutorialEnabled(Player player) { return bool(player, "tutorial", "preferences.defaults.tutorial", true); }
    public boolean tpStatusNotificationsEnabled(Player player) { return bool(player, "tp-status-notifications", "preferences.defaults.tp-status-notifications", true); }
    public boolean reportStaffNotificationsEnabled(Player player) { return bool(player, "report-staff-notifications", "preferences.defaults.report-staff-notifications", true); }

    public MenuMode menuMode(Player player) {
        if (!enabled()) return defaultMode();
        String raw = data.getString(path(player.getUniqueId(), "menu-mode"), defaultMode().name());
        try { return MenuMode.valueOf(raw == null ? "FULL" : raw.trim().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { return defaultMode(); }
    }

    public boolean compact(Player player) { return menuMode(player) == MenuMode.COMPACT; }

    public String defaultMenu(Player player) {
        String fallback = normalizeMenu(plugin.getConfig().getString("preferences.defaults.default-menu", "main"));
        String raw = enabled() ? data.getString(path(player.getUniqueId(), "default-menu"), fallback) : fallback;
        String normalized = normalizeMenu(raw);
        if (plugin.menus() == null || plugin.menus().getMenu(normalized) == null) return "main";
        return normalized;
    }

    public boolean setSounds(Player player, boolean value) { return set(player.getUniqueId(), "sounds", value); }
    public boolean setTutorial(Player player, boolean value) { return set(player.getUniqueId(), "tutorial", value); }
    public boolean setTpStatusNotifications(Player player, boolean value) { return set(player.getUniqueId(), "tp-status-notifications", value); }
    public boolean setReportStaffNotifications(Player player, boolean value) { return set(player.getUniqueId(), "report-staff-notifications", value); }
    public boolean setMenuMode(Player player, MenuMode mode) { return set(player.getUniqueId(), "menu-mode", (mode == null ? MenuMode.FULL : mode).name()); }

    public boolean setDefaultMenu(Player player, String menuId) {
        String normalized = normalizeMenu(menuId);
        if (plugin.menus() == null || plugin.menus().getMenu(normalized) == null) return false;
        return set(player.getUniqueId(), "default-menu", normalized);
    }

    public boolean reset(Player player) {
        data.set("players." + player.getUniqueId(), null);
        return save();
    }

    public List<String> availableMenus() {
        List<String> out = new ArrayList<>();
        out.add("main");
        ConfigurationSection section = plugin.getConfig().getConfigurationSection("menu.submenus");
        if (section != null) {
            section.getKeys(false).stream().map(this::normalizeMenu).filter(id -> !id.equals("main"))
                    .sorted(String.CASE_INSENSITIVE_ORDER).forEach(out::add);
        }
        return List.copyOf(out);
    }

    private boolean bool(Player player, String key, String configPath, boolean fallback) {
        boolean def = plugin.getConfig().getBoolean(configPath, fallback);
        if (!enabled()) return def;
        return data.getBoolean(path(player.getUniqueId(), key), def);
    }

    private MenuMode defaultMode() {
        String raw = plugin.getConfig().getString("preferences.defaults.menu-mode", "FULL");
        try { return MenuMode.valueOf(raw == null ? "FULL" : raw.trim().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { return MenuMode.FULL; }
    }

    private boolean set(UUID uuid, String key, Object value) {
        if (!enabled()) return false;
        data.set(path(uuid, key), value);
        if (save()) return true;
        data = YamlConfiguration.loadConfiguration(file);
        return false;
    }

    private String path(UUID uuid, String key) { return "players." + uuid + "." + key; }
    private String normalizeMenu(String raw) { return raw == null || raw.isBlank() ? "main" : raw.trim().toLowerCase(Locale.ROOT); }

    private boolean save() {
        try { data.save(file); return true; }
        catch (IOException exception) {
            plugin.getLogger().warning("Could not save preferences.yml: " + exception.getMessage());
            return false;
        }
    }
}
