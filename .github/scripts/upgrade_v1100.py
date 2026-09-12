from pathlib import Path

root = Path('.')

def read(path): return (root / path).read_text()
def write(path, content):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)
def insert_before(text, marker, block, label):
    if marker not in text:
        raise SystemExit(f'marker not found: {label}')
    return text.replace(marker, block + marker, 1)

# Versions
p='pom.xml'; s=read(p); s=replace_once(s,'<version>1.9.8</version>','<version>1.10.0</version>','pom version'); write(p,s)
p='src/main/resources/plugin.yml'; s=read(p); s=replace_once(s,"version: '1.9.8'","version: '1.10.0'",'plugin version'); write(p,s)

# Preference service
write('src/main/java/id/cadera/memberbook/preference/PreferenceService.java', r'''package id.cadera.memberbook.preference;

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
''')

# Main plugin wiring + migration
p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
s=replace_once(s,'import id.cadera.memberbook.report.ReportService;\n','import id.cadera.memberbook.report.ReportService;\nimport id.cadera.memberbook.preference.PreferenceService;\n','plugin pref import')
s=replace_once(s,'    private ReportService reportService;\n','    private ReportService reportService;\n    private PreferenceService preferenceService;\n','plugin pref field')
s=replace_once(s,'        menuActionService = new MenuActionService(this);\n        ToggleStore toggleStore = new ToggleStore(this);\n','        menuActionService = new MenuActionService(this);\n        preferenceService = new PreferenceService(this);\n        ToggleStore toggleStore = new ToggleStore(this);\n','plugin pref init')
s=s.replace('getLogger().info("CdrMemberBook v1.9.6 enabled.");','getLogger().info("CdrMemberBook v1.10.0 enabled.");')
block='''        if (configVersion < 26) {\n            getConfig().set("preferences.enabled", true);\n            getConfig().set("preferences.defaults.sounds", true);\n            getConfig().set("preferences.defaults.tutorial", true);\n            getConfig().set("preferences.defaults.tp-status-notifications", true);\n            getConfig().set("preferences.defaults.report-staff-notifications", true);\n            getConfig().set("preferences.defaults.menu-mode", "FULL");\n            getConfig().set("preferences.defaults.default-menu", "main");\n            if (!getConfig().isSet("menu.main.buttons.settings.enabled")) {\n                getConfig().set("menu.main.buttons.settings.enabled", true);\n                getConfig().set("menu.main.buttons.settings.name", "&dSettings");\n                getConfig().set("menu.main.buttons.settings.type", "settings");\n                getConfig().set("menu.main.buttons.settings.order", 900);\n                getConfig().set("menu.main.buttons.settings.icon", "textures/items/comparator");\n                getConfig().set("menu.main.buttons.settings.java-material", "COMPARATOR");\n                getConfig().set("menu.main.buttons.settings.permission", "");\n            }\n        }\n\n'''
s=insert_before(s,'        getConfig().set("config-version", 25);\n',block,'migration v26')
s=replace_once(s,'        getConfig().set("config-version", 25);\n','        getConfig().set("config-version", 26);\n','config version 26')
s=replace_once(s,'    public void openMenu(Player player) { openMenu(player, "main"); }\n','    public void openMenu(Player player) {\n        openMenu(player, preferenceService == null ? "main" : preferenceService.defaultMenu(player));\n    }\n','preferred default menu')
s=replace_once(s,'    public ReportService reports() {\n        return reportService;\n    }\n','    public ReportService reports() {\n        return reportService;\n    }\n\n    public PreferenceService preferences() {\n        return preferenceService;\n    }\n','pref getter')
write(p,s)

# Config v26 + defaults + settings button/messages
p='src/main/resources/config.yml'; s=read(p)
s=replace_once(s,'# CdrMemberBook v1.9.8\nconfig-version: 25','# CdrMemberBook v1.10.0\nconfig-version: 26','config header')
prefs='''# Per-player preferences. Data tersimpan ringan di plugins/CdrMemberBook/preferences.yml.\npreferences:\n  enabled: true\n  defaults:\n    sounds: true\n    tutorial: true\n    # Hanya feedback/status TPA non-kritis. Alert request masuk + tombol accept/deny tetap selalu tampil.\n    tp-status-notifications: true\n    # Berlaku saat player memiliki permission staff report.\n    report-staff-notifications: true\n    menu-mode: FULL\n    default-menu: main\n\n'''
s=insert_before(s,'# Java inventory GUI presentation. /menu on Java opens this native GUI.\n',prefs,'config preferences')
s=s.replace('#   report-center = native Bedrock staff Report Center\n','#   report-center = native Java/Bedrock staff Report Center\n#   settings = native per-player Settings / Preferences\n')
settings_button='''      settings:\n        enabled: true\n        name: '&dSettings'\n        type: settings\n        order: 900\n        icon: textures/items/comparator\n        java-material: COMPARATOR\n        permission: ''\n        lore:\n        - '&7Atur suara, tutorial, notifikasi,'\n        - '&7mode tampilan, dan default menu.'\n\n'''
s=insert_before(s,'      close:\n',settings_button,'settings button')
s=replace_once(s,"  config-reloaded: '&aConfig CdrMemberBook berhasil direload.'\n","  config-reloaded: '&aConfig CdrMemberBook berhasil direload.'\n  preference-updated: '&aPreference &f%setting% &aberhasil diubah menjadi &f%value%&a.'\n  preference-reset: '&aSemua preference kamu dikembalikan ke default server.'\n  preference-save-failed: '&cPreference gagal disimpan. Coba lagi atau cek storage server.'\n",'pref messages')
write(p,s)

# MenuConfig settings type
p='src/main/java/id/cadera/memberbook/menu/MenuConfigService.java'; s=read(p)
s=replace_once(s,'Set.of("command", "teleport", "homes", "pay", "trade", "report", "report-center", "submenu", "close")','Set.of("command", "teleport", "homes", "pay", "trade", "report", "report-center", "settings", "submenu", "close")','known settings type')
s=replace_once(s,'            case "teleport","close" -> new Availability(true,"ok","built-in");','            case "teleport","close","settings" -> new Availability(true,"ok","built-in");','settings availability')
write(p,s)

# Sounds preference
p='src/main/java/id/cadera/memberbook/util/Sounds.java'; s=read(p)
s=replace_once(s,'    public static void play(CdrMemberBookPlugin plugin, Player player, String configPath) {\n        String raw = plugin.getConfig().getString(configPath, "");','    public static void play(CdrMemberBookPlugin plugin, Player player, String configPath) {\n        if (plugin.preferences() != null && !plugin.preferences().soundsEnabled(player)) return;\n        String raw = plugin.getConfig().getString(configPath, "");','sound preference')
write(p,s)

# Advanced action sound preference
p='src/main/java/id/cadera/memberbook/menu/MenuActionService.java'; s=read(p)
s=replace_once(s,'                case "sound" -> {\n                    Sound sound = Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT));\n                    player.playSound(player.getLocation(), sound, action.volume(), action.pitch());\n                }','                case "sound" -> {\n                    if (plugin.preferences() == null || plugin.preferences().soundsEnabled(player)) {\n                        Sound sound = Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT));\n                        player.playSound(player.getLocation(), sound, action.volume(), action.pitch());\n                    }\n                }','action sound preference')
write(p,s)

# Tutorial auto preference
p='src/main/java/id/cadera/memberbook/tutorial/FirstJoinTutorialService.java'; s=read(p)
s=replace_once(s,'        if (!plugin.getConfig().getBoolean("tutorial.enabled", true)) return;\n        if (plugin.getConfig().getBoolean("tutorial.bedrock-only", true)','        if (!plugin.getConfig().getBoolean("tutorial.enabled", true)) return;\n        if (plugin.preferences() != null && !plugin.preferences().tutorialEnabled(player)) return;\n        if (plugin.getConfig().getBoolean("tutorial.bedrock-only", true)','tutorial preference')
write(p,s)

# Staff report notification preference
p='src/main/java/id/cadera/memberbook/report/ReportService.java'; s=read(p)
s=replace_once(s,'        for (Player online : Bukkit.getOnlinePlayers()) if (permission == null || permission.isBlank() || online.hasPermission(permission)) online.sendMessage(Colors.legacy(message));','        for (Player online : Bukkit.getOnlinePlayers()) {\n            if (permission != null && !permission.isBlank() && !online.hasPermission(permission)) continue;\n            if (plugin.preferences() != null && !plugin.preferences().reportStaffNotificationsEnabled(online)) continue;\n            online.sendMessage(Colors.legacy(message));\n        }','report staff pref')
write(p,s)

# TPA status preference. Functional incoming alert/controls stay mandatory.
p='src/main/java/id/cadera/memberbook/tp/TeleportRequestManager.java'; s=read(p)
s=replace_once(s,'        if (mode == TeleportMode.TO_TARGET) {\n            plugin.message(requester, "request-sent-to", "%player%", target.getName());\n            plugin.message(target, "request-received-to", "%player%", requester.getName());\n        } else {\n            plugin.message(requester, "request-sent-here", "%player%", target.getName());\n            plugin.message(target, "request-received-here", "%player%", requester.getName());\n        }','        if (mode == TeleportMode.TO_TARGET) {\n            statusMessage(requester, "request-sent-to", "%player%", target.getName());\n            plugin.message(target, "request-received-to", "%player%", requester.getName());\n        } else {\n            statusMessage(requester, "request-sent-here", "%player%", target.getName());\n            plugin.message(target, "request-received-here", "%player%", requester.getName());\n        }','tpa creation status')
s=s.replace('        plugin.message(target, "request-accepted");\n        plugin.message(requester, "request-accepted");','        statusMessage(target, "request-accepted");\n        statusMessage(requester, "request-accepted");')
s=s.replace('        plugin.message(target, "request-denied");','        statusMessage(target, "request-denied");')
s=s.replace('            plugin.message(requester, "target-denied", "%player%", target.getName());','            statusMessage(requester, "target-denied", "%player%", target.getName());')
s=s.replace('                plugin.message(requester, "request-expired-sender", "%player%", target == null ? "player" : target.getName());','                statusMessage(requester, "request-expired-sender", "%player%", target == null ? "player" : target.getName());')
s=s.replace('                plugin.message(target, "request-expired-target", "%player%", requester == null ? "player" : requester.getName());','                statusMessage(target, "request-expired-target", "%player%", requester == null ? "player" : requester.getName());')
helper='''    private void statusMessage(Player player, String key, String... replacements) {\n        if (plugin.preferences() != null && !plugin.preferences().tpStatusNotificationsEnabled(player)) return;\n        plugin.message(player, key, replacements);\n    }\n\n'''
s=insert_before(s,'    private void sendAcceptControls(Player target, Player requester, TeleportMode mode) {\n',helper,'tpa status helper')
write(p,s)

# MenuHolder settings states
p='src/main/java/id/cadera/memberbook/gui/MenuHolder.java'; s=read(p)
s=replace_once(s,'        TP_MODE,\n        REPORT_CENTER,','        TP_MODE,\n        SETTINGS,\n        SETTINGS_DEFAULT_MENU,\n        REPORT_CENTER,','settings holder states')
write(p,s)

# Java Settings UI
p='src/main/java/id/cadera/memberbook/gui/JavaMenuService.java'; s=read(p)
s=replace_once(s,'import id.cadera.memberbook.report.ReportService;\n','import id.cadera.memberbook.report.ReportService;\nimport id.cadera.memberbook.preference.PreferenceService;\n','java pref import')
s=replace_once(s,'    private static final String REPORT_PREFIX = "__report:";\n','    private static final String PREF_SOUNDS = "__pref_sounds";\n    private static final String PREF_TUTORIAL = "__pref_tutorial";\n    private static final String PREF_TP_NOTIFY = "__pref_tp_notify";\n    private static final String PREF_REPORT_NOTIFY = "__pref_report_notify";\n    private static final String PREF_MENU_MODE = "__pref_menu_mode";\n    private static final String PREF_DEFAULT_MENU = "__pref_default_menu";\n    private static final String PREF_DEFAULT_PREFIX = "__pref_default:";\n    private static final String PREF_RESET = "__pref_reset";\n    private static final String REPORT_PREFIX = "__report:";\n','java pref constants')
s=replace_once(s,'            case TP_MODE -> handleTpMode(player, holder, event.getSlot());\n            case REPORT_CENTER','            case TP_MODE -> handleTpMode(player, holder, event.getSlot());\n            case SETTINGS -> handleSettingsClick(player, holder, clicked);\n            case SETTINGS_DEFAULT_MENU -> handleDefaultMenuClick(player, holder, clicked);\n            case REPORT_CENTER','java settings click cases')
s=replace_once(s,'            case "report-center" -> showReportCenter(player, menu.id());\n            case "submenu"','            case "report-center" -> showReportCenter(player, menu.id());\n            case "settings" -> showSettings(player, menu.id());\n            case "submenu"','java settings button')
# Compact configured item behavior
s=replace_once(s,'        List<String> lore = new ArrayList<>();\n        if (button.lore() != null) for (String line : button.lore()) lore.add(plugin.formatMenuText(line, player));\n        if (plugin.getConfig().getBoolean("java-menu.decorations.click-hint", true)) {','        List<String> lore = new ArrayList<>();\n        boolean compact = plugin.preferences() != null && plugin.preferences().compact(player);\n        if (!compact && button.lore() != null) for (String line : button.lore()) lore.add(plugin.formatMenuText(line, player));\n        if (!compact && plugin.getConfig().getBoolean("java-menu.decorations.click-hint", true)) {','java compact lore')
settings_methods=r'''    // ---- Player Preferences ----

    private void showSettings(Player player, String returnMenuId) {
        if (plugin.preferences() == null || !plugin.preferences().enabled()) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, returnMenuId, 0);
            return;
        }
        PreferenceService prefs = plugin.preferences();
        MenuHolder holder = new MenuHolder(MenuHolder.Type.SETTINGS, null, returnMenuId, 0, 36,
                "§8CdrMemberBook §7• §dSettings");
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));
        inventory.setItem(4, playerInfoItem(player, 0, 1, "Player Settings"));
        inventory.setItem(10, navigationItem(prefs.soundsEnabled(player) ? Material.NOTE_BLOCK : Material.BARRIER,
                prefName("Suara Plugin", prefs.soundsEnabled(player)), PREF_SOUNDS, "&7Toggle suara CdrMemberBook termasuk action sound."));
        inventory.setItem(11, navigationItem(prefs.tutorialEnabled(player) ? Material.BOOK : Material.PAPER,
                prefName("Tutorial Otomatis", prefs.tutorialEnabled(player)), PREF_TUTORIAL, "&7Atur tutorial otomatis saat join. Manual tutorial tetap bisa dipanggil admin."));
        inventory.setItem(12, navigationItem(prefs.tpStatusNotificationsEnabled(player) ? Material.ENDER_PEARL : Material.GRAY_DYE,
                prefName("TP Status Notification", prefs.tpStatusNotificationsEnabled(player)), PREF_TP_NOTIFY,
                "&7Toggle feedback status TPA.\n&8Request masuk + accept/deny tetap selalu tampil."));
        inventory.setItem(14, navigationItem(prefs.reportStaffNotificationsEnabled(player) ? Material.BELL : Material.GRAY_DYE,
                prefName("Staff Report Notification", prefs.reportStaffNotificationsEnabled(player)), PREF_REPORT_NOTIFY,
                "&7Dipakai saat kamu memiliki permission staff report."));
        inventory.setItem(15, navigationItem(Material.COMPARATOR, "&dMenu Mode: &f" + prefs.menuMode(player), PREF_MENU_MODE,
                "&7FULL = lore + petunjuk lengkap.\n&7COMPACT = tampilan menu lebih ringkas."));
        inventory.setItem(16, navigationItem(Material.COMPASS, "&bDefault Menu: &f" + prefs.defaultMenu(player), PREF_DEFAULT_MENU,
                "&7Menu pertama yang terbuka saat /menu atau Member Book dipakai."));
        inventory.setItem(30, navigationItem(Material.REDSTONE_TORCH, "&eReset ke Default", PREF_RESET,
                "&7Hapus preference pribadi dan kembali ke default server."));
        inventory.setItem(31, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke menu sebelumnya."));
        player.openInventory(inventory);
    }

    private void handleSettingsClick(Player player, MenuHolder holder, ItemStack clicked) {
        String action = action(clicked);
        if (action == null || plugin.preferences() == null) return;
        PreferenceService prefs = plugin.preferences();
        if (NAV_BACK.equals(action)) { showConfiguredMenu(player, holder.menuId(), 0); return; }
        if (PREF_DEFAULT_MENU.equals(action)) { showDefaultMenuPicker(player, holder.menuId()); return; }
        boolean ok;
        String setting;
        String value;
        switch (action) {
            case PREF_SOUNDS -> { boolean next=!prefs.soundsEnabled(player); ok=prefs.setSounds(player,next); setting="sounds"; value=onOff(next); }
            case PREF_TUTORIAL -> { boolean next=!prefs.tutorialEnabled(player); ok=prefs.setTutorial(player,next); setting="tutorial"; value=onOff(next); }
            case PREF_TP_NOTIFY -> { boolean next=!prefs.tpStatusNotificationsEnabled(player); ok=prefs.setTpStatusNotifications(player,next); setting="tp-status-notifications"; value=onOff(next); }
            case PREF_REPORT_NOTIFY -> { boolean next=!prefs.reportStaffNotificationsEnabled(player); ok=prefs.setReportStaffNotifications(player,next); setting="report-staff-notifications"; value=onOff(next); }
            case PREF_MENU_MODE -> { PreferenceService.MenuMode next=prefs.menuMode(player)==PreferenceService.MenuMode.FULL ? PreferenceService.MenuMode.COMPACT : PreferenceService.MenuMode.FULL; ok=prefs.setMenuMode(player,next); setting="menu-mode"; value=next.name(); }
            case PREF_RESET -> { ok=prefs.reset(player); setting="reset"; value="DEFAULT"; if(ok) plugin.message(player,"preference-reset"); }
            default -> { return; }
        }
        if (!ok) plugin.message(player, "preference-save-failed");
        else if (!PREF_RESET.equals(action)) plugin.message(player,"preference-updated","%setting%",setting,"%value%",value);
        showSettings(player, holder.menuId());
    }

    private void showDefaultMenuPicker(Player player, String returnMenuId) {
        if (plugin.preferences() == null) return;
        List<String> menus = plugin.preferences().availableMenus();
        MenuHolder holder = new MenuHolder(MenuHolder.Type.SETTINGS_DEFAULT_MENU, null, returnMenuId, 0, 54,
                "§8Settings §7• §bDefault Menu");
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, 0, 1, "Default Menu");
        int i=0;
        for (String id : menus) {
            if (i >= CONTENT_SLOTS.length) break;
            boolean current = id.equalsIgnoreCase(plugin.preferences().defaultMenu(player));
            inventory.setItem(CONTENT_SLOTS[i++], navigationItem(current ? Material.LIME_DYE : Material.PAPER,
                    (current ? "&a" : "&f") + id, PREF_DEFAULT_PREFIX + id,
                    current ? "&7Default menu saat ini." : "&7Klik untuk jadikan default menu."));
        }
        inventory.setItem(49, navigationItem(Material.OAK_DOOR,"&eKembali",NAV_BACK,"&7Kembali ke Settings."));
        player.openInventory(inventory);
    }

    private void handleDefaultMenuClick(Player player, MenuHolder holder, ItemStack clicked) {
        String action=action(clicked);
        if (action==null || plugin.preferences()==null) return;
        if (NAV_BACK.equals(action)) { showSettings(player, holder.menuId()); return; }
        if (!action.startsWith(PREF_DEFAULT_PREFIX)) return;
        String menu=action.substring(PREF_DEFAULT_PREFIX.length());
        if (!plugin.preferences().setDefaultMenu(player, menu)) plugin.message(player,"preference-save-failed");
        else plugin.message(player,"preference-updated","%setting%","default-menu","%value%",menu);
        showSettings(player, holder.menuId());
    }

    private String prefName(String label, boolean value) { return (value ? "&a" : "&c") + label + ": &f" + onOff(value); }
    private String onOff(boolean value) { return value ? "ON" : "OFF"; }

'''
s=insert_before(s,'    // ---- Java Staff Report Center ----\n',settings_methods,'java settings methods')
write(p,s)

# Bedrock settings UI
p='src/main/java/id/cadera/memberbook/form/BedrockFormService.java'; s=read(p)
s=replace_once(s,'import id.cadera.memberbook.report.ReportService;\n','import id.cadera.memberbook.report.ReportService;\nimport id.cadera.memberbook.preference.PreferenceService;\n','bedrock pref import')
s=replace_once(s,'        SimpleForm.Builder builder = SimpleForm.builder()\n                .title(plugin.formatMenuText(menu.title(), player))\n                .content(plugin.formatMenuText(menu.content(), player));','        SimpleForm.Builder builder = SimpleForm.builder()\n                .title(plugin.formatMenuText(menu.title(), player))\n                .content(plugin.preferences() != null && plugin.preferences().compact(player)\n                        ? "" : plugin.formatMenuText(menu.content(), player));','bedrock compact content')
s=replace_once(s,'            case "report-center" -> showReportCenter(player, menu.id());\n            case "submenu"','            case "report-center" -> showReportCenter(player, menu.id());\n            case "settings" -> showSettingsForm(player, menu.id());\n            case "submenu"','bedrock settings button')
bedrock_methods=r'''    // ---- Player Preferences ----

    private void showSettingsForm(Player player, String returnMenuId) {
        if (plugin.preferences() == null || !plugin.preferences().enabled()) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, returnMenuId);
            return;
        }
        PreferenceService p = plugin.preferences();
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Player Settings")
                .content("Preference tersimpan per-player.\nDefault menu: " + p.defaultMenu(player) + "\nMode: " + p.menuMode(player));
        addButton(builder, "Suara Plugin: " + onOff(p.soundsEnabled(player)), "settings", "textures/items/note_block");
        addButton(builder, "Tutorial Otomatis: " + onOff(p.tutorialEnabled(player)), "settings", "textures/items/book_written");
        addButton(builder, "TP Status Notification: " + onOff(p.tpStatusNotificationsEnabled(player)), "settings", "textures/items/ender_pearl");
        addButton(builder, "Staff Report Notification: " + onOff(p.reportStaffNotificationsEnabled(player)), "settings", "textures/items/bell");
        addButton(builder, "Menu Mode: " + p.menuMode(player), "settings", "textures/items/comparator");
        addButton(builder, "Default Menu: " + p.defaultMenu(player), "settings", "textures/items/compass_item");
        addButton(builder, "Reset ke Default", "delete", "textures/items/redstone_dust");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!player.isOnline() || plugin.preferences() == null) return;
            PreferenceService prefs=plugin.preferences();
            int selected=response.clickedButtonId();
            boolean ok=true; String setting=null; String value=null;
            switch(selected) {
                case 0 -> { boolean next=!prefs.soundsEnabled(player); ok=prefs.setSounds(player,next); setting="sounds"; value=onOff(next); }
                case 1 -> { boolean next=!prefs.tutorialEnabled(player); ok=prefs.setTutorial(player,next); setting="tutorial"; value=onOff(next); }
                case 2 -> { boolean next=!prefs.tpStatusNotificationsEnabled(player); ok=prefs.setTpStatusNotifications(player,next); setting="tp-status-notifications"; value=onOff(next); }
                case 3 -> { boolean next=!prefs.reportStaffNotificationsEnabled(player); ok=prefs.setReportStaffNotifications(player,next); setting="report-staff-notifications"; value=onOff(next); }
                case 4 -> { PreferenceService.MenuMode next=prefs.menuMode(player)==PreferenceService.MenuMode.FULL ? PreferenceService.MenuMode.COMPACT : PreferenceService.MenuMode.FULL; ok=prefs.setMenuMode(player,next); setting="menu-mode"; value=next.name(); }
                case 5 -> { showDefaultMenuForm(player, returnMenuId); return; }
                case 6 -> { ok=prefs.reset(player); if(ok) plugin.message(player,"preference-reset"); }
                case 7 -> { showConfiguredMenu(player, returnMenuId); return; }
                default -> { return; }
            }
            if (!ok) plugin.message(player,"preference-save-failed");
            else if (setting != null) plugin.message(player,"preference-updated","%setting%",setting,"%value%",value);
            showSettingsForm(player,returnMenuId);
        })).build());
    }

    private void showDefaultMenuForm(Player player, String returnMenuId) {
        if (plugin.preferences()==null) return;
        List<String> menus=plugin.preferences().availableMenus();
        SimpleForm.Builder builder=SimpleForm.builder().title("Default Menu")
                .content("Pilih menu yang pertama terbuka saat /menu atau Member Book dipakai.");
        for(String id:menus) addButton(builder,(id.equalsIgnoreCase(plugin.preferences().defaultMenu(player))?"✓ ":"")+id,"settings","textures/items/paper");
        addButton(builder,"Kembali","back","textures/items/arrow");
        int back=menus.size();
        send(player,builder.validResultHandler(response -> sync(() -> {
            int selected=response.clickedButtonId();
            if(selected==back){showSettingsForm(player,returnMenuId);return;}
            if(selected<0 || selected>=menus.size()) return;
            String menu=menus.get(selected);
            if(!plugin.preferences().setDefaultMenu(player,menu)) plugin.message(player,"preference-save-failed");
            else plugin.message(player,"preference-updated","%setting%","default-menu","%value%",menu);
            showSettingsForm(player,returnMenuId);
        })).build());
    }

    private String onOff(boolean value) { return value ? "ON" : "OFF"; }

'''
s=insert_before(s,'    private void showHomesMenu(Player player, String returnMenuId, String fallbackCommand) {\n',bedrock_methods,'bedrock settings methods')
write(p,s)

# Update admin displayed version
p='src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'; s=read(p); s=s.replace('v1.9.6','v1.10.0').replace('v1.9.8','v1.10.0'); write(p,s)

# Docs
p='README.md'; s=read(p); s=s.replace('# CdrMemberBook v1.9.7','# CdrMemberBook v1.10.0',1).replace('# CdrMemberBook v1.9.8','# CdrMemberBook v1.10.0',1)
section=r'''
## Player Preferences — v1.10.0

CdrMemberBook now stores lightweight per-player preferences in `plugins/CdrMemberBook/preferences.yml`.
Java and Bedrock players can open the native `Settings` button from `/menu` and configure:

- plugin/menu sounds ON/OFF
- automatic first-join tutorial ON/OFF
- non-critical TPA status notifications ON/OFF (incoming request + accept/deny controls remain visible for safety)
- staff report notifications ON/OFF
- menu presentation mode FULL / COMPACT
- default menu opened by `/menu` or Member Book
- reset all personal preferences back to server defaults

The default values remain server-configurable under `preferences.defaults.*`. Existing players require no migration; missing keys use server defaults automatically.

'''
if '## Player Preferences — v1.10.0' not in s:
    idx=s.find('\n## ')
    s=s[:idx+1]+section+s[idx+1:] if idx>=0 else s+section
write(p,s)

p='CHANGELOG.md'; s=read(p)
entry=r'''## 1.10.0 - Player Preferences

- Added lightweight persistent `preferences.yml` storage per player UUID.
- Added native Java and Bedrock Settings UI with sounds, tutorial, TPA status notification, staff report notification, menu mode and default-menu controls.
- Added FULL / COMPACT menu presentation preference.
- `/menu` and Member Book now honor each player's selected default menu.
- Wired sound preferences into built-in teleport sounds and advanced menu sound actions.
- Wired tutorial preference into automatic first-join tutorial delivery.
- Wired report notification preference into staff report chat alerts.
- Added safe TPA status-notification preference while keeping incoming request and accept/deny controls visible.
- Added reset-to-server-defaults and config migration v26.

'''
s=replace_once(s,'# Changelog\n\n','# Changelog\n\n'+entry,'changelog v1100')
write(p,s)
