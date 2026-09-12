package id.cadera.memberbook;

import org.bukkit.Bukkit;
import org.bukkit.NamespacedKey;
import org.bukkit.command.PluginCommand;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerChangedWorldEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;
import id.cadera.memberbook.command.MemberBookAdminCommand;
import id.cadera.memberbook.admin.AdminMenuEditorService;
import id.cadera.memberbook.command.MenuCommand;
import id.cadera.memberbook.command.TeleportCommands;
import id.cadera.memberbook.form.BedrockFormService;
import id.cadera.memberbook.gui.JavaMenuService;
import id.cadera.memberbook.integration.EssentialsHomeService;
import id.cadera.memberbook.item.MemberBookService;
import id.cadera.memberbook.menu.MenuConfigService;
import id.cadera.memberbook.menu.MenuActionService;
import id.cadera.memberbook.menu.MenuConfigService.MenuButton;
import id.cadera.memberbook.report.ReportService;
import id.cadera.memberbook.preference.PreferenceService;
import id.cadera.memberbook.tp.TeleportRequestManager;
import id.cadera.memberbook.tp.ToggleStore;
import id.cadera.memberbook.tutorial.FirstJoinTutorialService;
import id.cadera.memberbook.util.Colors;

import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public final class CdrMemberBookPlugin extends JavaPlugin implements Listener {
    private TeleportRequestManager requestManager;
    private BedrockFormService formService;
    private JavaMenuService javaMenuService;
    private MemberBookService memberBookService;
    private MenuConfigService menuConfigService;
    private MenuActionService menuActionService;
    private EssentialsHomeService essentialsHomeService;
    private FirstJoinTutorialService tutorialService;
    private ReportService reportService;
    private PreferenceService preferenceService;
    private AdminMenuEditorService adminMenuEditorService;
    private NamespacedKey playerKey;
    private NamespacedKey buttonKey;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        migrateAndMergeConfig();
        getDataFolder().mkdirs();
        playerKey = new NamespacedKey(this, "target-player");
        buttonKey = new NamespacedKey(this, "menu-button");

        menuConfigService = new MenuConfigService(this);
        menuActionService = new MenuActionService(this);
        preferenceService = new PreferenceService(this);
        adminMenuEditorService = new AdminMenuEditorService(this);
        ToggleStore toggleStore = new ToggleStore(this);
        requestManager = new TeleportRequestManager(this, toggleStore);
        javaMenuService = new JavaMenuService(this);
        memberBookService = new MemberBookService(this);
        reportService = new ReportService(this);

        if (Bukkit.getPluginManager().isPluginEnabled("Essentials")) {
            try {
                essentialsHomeService = new EssentialsHomeService(this);
                if (essentialsHomeService.initialize()) {
                    getLogger().info("EssentialsX detected: Bedrock Home Manager enabled.");
                } else {
                    essentialsHomeService = null;
                    getLogger().warning("Essentials plugin detected but Home integration could not initialize.");
                }
            } catch (Throwable throwable) {
                essentialsHomeService = null;
                getLogger().warning("EssentialsX Home integration unavailable: " + throwable.getMessage());
            }
        } else {
            getLogger().info("EssentialsX not detected: special Home Manager will show a dependency warning.");
        }

        if (Bukkit.getPluginManager().isPluginEnabled("floodgate")) {
            try {
                formService = new BedrockFormService(this);
                getLogger().info("Floodgate detected: native Bedrock forms enabled.");
            } catch (Throwable throwable) {
                formService = null;
                getLogger().warning("Floodgate was detected but Forms could not initialize: " + throwable.getMessage());
            }
        } else {
            getLogger().info("Floodgate not detected: Java inventory fallback only.");
        }

        if (Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI")) {
            getLogger().info("PlaceholderAPI detected: Dynamic Member Book placeholders enabled.");
        } else {
            getLogger().info("PlaceholderAPI not detected: Dynamic Member Book will use built-in placeholders only.");
        }

        tutorialService = new FirstJoinTutorialService(this);
        registerCommands();
        Bukkit.getPluginManager().registerEvents(this, this);
        Bukkit.getPluginManager().registerEvents(javaMenuService, this);
        Bukkit.getPluginManager().registerEvents(adminMenuEditorService, this);
        Bukkit.getPluginManager().registerEvents(memberBookService, this);
        Bukkit.getPluginManager().registerEvents(tutorialService, this);
        memberBookService.validateConfiguration();
        menuConfigService.validateConfiguration();
        memberBookService.giveToOnlinePlayers();
        memberBookService.startEnforcement();
        getLogger().info("Member Book mode: " + memberBookService.modeName());
        getLogger().info("CdrMemberBook v1.11.0.1 enabled.");
    }

    @Override
    public void onDisable() {
        if (memberBookService != null) memberBookService.stopEnforcement();
        if (menuActionService != null) menuActionService.shutdown();
    }

    private void migrateAndMergeConfig() {
        boolean hadDynamicMenu = getConfig().isConfigurationSection("menu.main.buttons");
        Map<String, String> legacyCommands = new HashMap<>();
        Map<String, String> legacyIcons = new HashMap<>();
        String[] legacyKeys = {"warp", "pwarp", "sethome", "land", "transfer", "bank", "team", "shop", "playershop", "report", "barter"};

        if (!hadDynamicMenu) {
            for (String key : legacyKeys) {
                String command = getConfig().getString("menu-actions." + key);
                if (command != null) legacyCommands.put(key, command);
                String icon = getConfig().getString("bedrock-icons." + key);
                if (icon != null) legacyIcons.put(key, icon);
            }
        }

        int configVersion = getConfig().getInt("config-version", hadDynamicMenu ? 2 : 1);
        getConfig().options().copyDefaults(true);

        if (!hadDynamicMenu) {
            for (Map.Entry<String, String> entry : legacyCommands.entrySet()) {
                getConfig().set("menu.main.buttons." + entry.getKey() + ".command", entry.getValue());
            }
            for (Map.Entry<String, String> entry : legacyIcons.entrySet()) {
                getConfig().set("menu.main.buttons." + entry.getKey() + ".icon", entry.getValue());
            }
        }

        if (configVersion < 3) {
            migrateSpecialButton("sethome", "sethome", "homes", "homes");
            migrateSpecialButton("transfer", "pay", "pay", "pay");
            migrateSpecialButton("barter", "trade", "trade", "axtrade");
        }

        if (configVersion < 4) {
            getConfig().set("member-book.permanent-hotbar", false);
            getConfig().set("member-book.prevent-move", false);
            getConfig().set("member-book.prevent-external-storage", true);
        }

        if (configVersion < 5) {
            getConfig().set("member-book.recovery.enabled", true);
            getConfig().set("member-book.recovery.interval-ticks", 100L);
            getConfig().set("member-book.recovery.recover-on-world-change", true);
            getConfig().set("member-book.recovery.recover-from-open-container", true);
            getConfig().set("member-book.recovery.remove-duplicates", true);
        }

        if (configVersion < 6) {
            getConfig().set("member-book.customization.custom-model-data", 0);
            getConfig().set("member-book.customization.item-model", "");
            getConfig().set("member-book.customization.enchant-glint", "default");
            getConfig().set("member-book.customization.hide-tooltip", false);
            getConfig().set("member-book.customization.hide-attributes", false);
            getConfig().set("member-book.customization.hide-additional-tooltip", false);
            getConfig().set("member-book.customization.item-flags", java.util.List.of());
            getConfig().set("member-book.customization.refresh-existing", true);
        }

        if (configVersion < 7) {
            getConfig().set("member-book.dynamic.enabled", true);
            getConfig().set("member-book.dynamic.placeholderapi", true);
            getConfig().set("member-book.dynamic.built-in-placeholders", true);
            getConfig().set("member-book.dynamic.refresh-interval-ticks", 200L);
            getConfig().set("member-book.dynamic.refresh-on-join", true);
            getConfig().set("member-book.dynamic.refresh-on-world-change", true);
        }

        if (configVersion < 8) {
            getConfig().set("integrations.essentials-home.presets", java.util.List.of("rumah", "base", "farm", "tambang", "shop"));
            getConfig().set("integrations.essentials-home.allow-custom-name", true);
        }

        if (configVersion < 9) {
            getConfig().set("member-book.open-cooldown-ticks", 20L);
            getConfig().set("integrations.essentials-home.sort-alphabetically", true);
            getConfig().set("integrations.essentials-home.show-refresh-button", true);
        }

        if (configVersion < 10) {
            getConfig().set("integrations.essentials-home.hide-locked-presets", true);
            getConfig().set("integrations.essentials-home.use-display-names-on-owned-homes", true);
            setPresetDefaults("rumah", "Rumah", "textures/items/bed_red");
            setPresetDefaults("base", "Base", "textures/items/bed_red");
            setPresetDefaults("farm", "Farm", "textures/items/wheat");
            setPresetDefaults("tambang", "Tambang", "textures/items/iron_pickaxe");
            setPresetDefaults("shop", "Shop", "textures/items/emerald");
        }

        if (configVersion < 11) {
            if (!getConfig().isSet("member-book.mode")) {
                getConfig().set("member-book.mode",
                        getConfig().getBoolean("member-book.permanent-hotbar", false)
                                ? "LOCKED_HOTBAR" : "MOVABLE");
            }
            getConfig().set("member-book.fixed-slot.return-delay-ticks", 40L);
        }

        if (configVersion < 12) {
            getConfig().set("tutorial.enabled", true);
            getConfig().set("tutorial.bedrock-only", true);
            getConfig().set("tutorial.show-to-existing-unseen", false);
            getConfig().set("tutorial.delay-ticks", 60L);
            getConfig().set("tutorial.open-menu-after-complete", true);
        }

        if (configVersion < 13) {
            getConfig().set("menu.hide-unavailable-buttons", true);
            getConfig().set("menu.auto-detect-command-dependencies", true);
            getConfig().set("integrations.report.enabled", true);
            getConfig().set("integrations.report.cooldown-seconds", 60L);
            getConfig().set("integrations.report.min-reason-length", 3);
            getConfig().set("integrations.report.max-reason-length", 200);
            getConfig().set("integrations.report.staff-permission", "cdrmemberbook.staff.report");
            getConfig().set("integrations.report.console-command", "");
            migrateSpecialButton("report", "report", "report", "report");
        }

        if (configVersion < 14) {
            migrateLegacyBranding();
        }

        if (configVersion < 15) {
            getConfig().set("menu.log-invalid-buttons", true);
        }

        if (configVersion < 16) {
            getConfig().set("integrations.report.admin-page-size", 8);
        }

        if (configVersion < 17) {
            getConfig().set("menu.actions.enabled", true);
        }

        if (configVersion < 18) {
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

        if (configVersion < 20) {
            getConfig().set("integrations.report.center.enabled", true);
            getConfig().set("integrations.report.center.page-size", 8);
            getConfig().set("integrations.report.center.allow-delete", true);
        }

        if (configVersion < 21) {
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

        if (configVersion < 23) {
            getConfig().set("integrations.report.java-submit.enabled", true);
            getConfig().set("integrations.report.java-submit.reason-title", "&8Lapor • Alasan");
            getConfig().set("integrations.report.java-submit.reason-placeholder", "Ketik alasan laporan...");
            getConfig().set("integrations.report.java-submit.reason-material", "PAPER");
        }

        if (configVersion < 24) {
            getConfig().set("integrations.report.categories.enabled", true);
            getConfig().set("integrations.report.categories.values", java.util.List.of("CHEATING", "GRIEFING", "TOXIC", "SCAM", "BUG_ABUSE", "OTHER"));
            getConfig().set("integrations.report.categories.labels.CHEATING", "Cheating / Hack");
            getConfig().set("integrations.report.categories.labels.GRIEFING", "Griefing");
            getConfig().set("integrations.report.categories.labels.TOXIC", "Toxic / Harassment");
            getConfig().set("integrations.report.categories.labels.SCAM", "Scam");
            getConfig().set("integrations.report.categories.labels.BUG_ABUSE", "Bug Abuse");
            getConfig().set("integrations.report.categories.labels.OTHER", "Lainnya");
            getConfig().set("integrations.report.evidence.enabled", true);
            getConfig().set("integrations.report.evidence.optional", true);
            getConfig().set("integrations.report.evidence.max-length", 300);
            getConfig().set("integrations.report.evidence.require-http-url-if-link", true);
            getConfig().set("integrations.report.java-submit.evidence-title", "&8Lapor • Evidence");
            getConfig().set("integrations.report.java-submit.evidence-placeholder", "Evidence opsional...");
        }

        if (configVersion < 25) {
            getConfig().set("integrations.report.center.show-category-filter", true);
            getConfig().set("integrations.report.center.java-search-title", "&8Reports • Search");
            getConfig().set("integrations.report.center.java-search-placeholder", "Ketik nama / UUID...");
            getConfig().set("integrations.report.center.java-note-title", "&8Report • Staff Note");
            getConfig().set("integrations.report.center.java-note-placeholder", "Ketik catatan staff...");
        }

        if (configVersion < 26) {
            getConfig().set("preferences.enabled", true);
            getConfig().set("preferences.defaults.sounds", true);
            getConfig().set("preferences.defaults.tutorial", true);
            getConfig().set("preferences.defaults.tp-status-notifications", true);
            getConfig().set("preferences.defaults.report-staff-notifications", true);
            getConfig().set("preferences.defaults.menu-mode", "FULL");
            getConfig().set("preferences.defaults.default-menu", "main");
            if (!getConfig().isSet("menu.main.buttons.settings.enabled")) {
                getConfig().set("menu.main.buttons.settings.enabled", true);
                getConfig().set("menu.main.buttons.settings.name", "&dSettings");
                getConfig().set("menu.main.buttons.settings.type", "settings");
                getConfig().set("menu.main.buttons.settings.order", 900);
                getConfig().set("menu.main.buttons.settings.icon", "textures/items/comparator");
                getConfig().set("menu.main.buttons.settings.java-material", "COMPARATOR");
                getConfig().set("menu.main.buttons.settings.permission", "");
            }
        }

        if (configVersion < 27) {
            getConfig().set("admin-menu-editor.enabled", true);
            getConfig().set("admin-menu-editor.permission", "cdrmemberbook.admin.memberbook");
            getConfig().set("admin-menu-editor.max-buttons-per-menu", 100);
        }

        if (configVersion < 28) {
            String material = getConfig().getString("member-book.material", "BOOK");
            if (material == null || material.isBlank() || material.equalsIgnoreCase("BOOK")) {
                getConfig().set("member-book.material", "WRITABLE_BOOK");
            }
            getConfig().set("member-book.interaction.hand-fallback", true);
            getConfig().set("member-book.interaction.bedrock-open-delay-ticks", 1L);
        }

        getConfig().set("config-version", 28);
        saveConfig();
    }

    private void migrateLegacyBranding() {
        for (String key : new java.util.ArrayList<>(getConfig().getKeys(true))) {
            Object value = getConfig().get(key);
            if (value instanceof String text) {
                getConfig().set(key, rebrandLegacyText(text));
                continue;
            }
            if (value instanceof java.util.List<?> list) {
                java.util.List<Object> rewritten = new java.util.ArrayList<>(list.size());
                boolean changed = false;
                for (Object entry : list) {
                    if (entry instanceof String text) {
                        String updated = rebrandLegacyText(text);
                        rewritten.add(updated);
                        if (!updated.equals(text)) changed = true;
                    } else {
                        rewritten.add(entry);
                    }
                }
                if (changed) getConfig().set(key, rewritten);
            }
        }
    }

    private String rebrandLegacyText(String text) {
        return text
                .replace("MOON" + "SIGN", "CdrMemberBook")
                .replace("Moon" + "Sign", "CdrMemberBook")
                .replace("moon" + "signmenu.", "cdrmemberbook.")
                .replace("moon" + "sign:", "cdrmemberbook:");
    }

    private void setPresetDefaults(String name, String displayName, String icon) {
        String base = "integrations.essentials-home.preset-details." + name + ".";
        if (!getConfig().isSet(base + "enabled")) getConfig().set(base + "enabled", true);
        if (!getConfig().isSet(base + "display-name")) getConfig().set(base + "display-name", displayName);
        if (!getConfig().isSet(base + "icon")) getConfig().set(base + "icon", icon);
        if (!getConfig().isSet(base + "permission")) getConfig().set(base + "permission", "");
    }

    private void migrateSpecialButton(String key, String expectedCommand, String newType, String fallbackCommand) {
        String base = "menu.main.buttons." + key;
        String type = getConfig().getString(base + ".type", "command");
        String command = getConfig().getString(base + ".command", "");
        String normalized = command == null ? "" : command.trim();
        if (normalized.startsWith("/")) normalized = normalized.substring(1);

        if ("command".equalsIgnoreCase(type) && normalized.equalsIgnoreCase(expectedCommand)) {
            getConfig().set(base + ".type", newType);
            getConfig().set(base + ".command", fallbackCommand);
        }
    }

    private void registerCommands() {
        MenuCommand menu = new MenuCommand(this);
        PluginCommand menuCommand = Objects.requireNonNull(getCommand("menu"));
        menuCommand.setExecutor(menu);
        menuCommand.setTabCompleter(menu);

        TeleportCommands tp = new TeleportCommands(this);
        for (String commandName : new String[]{"tpa", "tpahere", "tpaccept", "tpdeny", "tptoggle"}) {
            PluginCommand command = Objects.requireNonNull(getCommand(commandName));
            command.setExecutor(tp);
            command.setTabCompleter(tp);
        }

        MemberBookAdminCommand memberBookAdmin = new MemberBookAdminCommand(this);
        PluginCommand memberBookCommand = Objects.requireNonNull(getCommand("cdrmemberbook"));
        memberBookCommand.setExecutor(memberBookAdmin);
        memberBookCommand.setTabCompleter(memberBookAdmin);
    }

    public void openMenu(Player player) {
        openMenu(player, preferenceService == null ? "main" : preferenceService.defaultMenu(player));
    }

    public void openMenu(Player player, String menuId) {
        String id = menuId == null || menuId.isBlank() ? "main" : menuId;
        if (formService != null && formService.isBedrock(player)) formService.showConfiguredMenu(player, id);
        else javaMenuService.showConfiguredMenu(player, id, 0);
    }

    public void reloadCdrMemberBookConfig() {
        reloadConfig();
        if (memberBookService != null) {
            memberBookService.validateConfiguration();
            menuConfigService.validateConfiguration();
            memberBookService.restartEnforcement();
            memberBookService.giveToOnlinePlayers();
        }
    }

    public TeleportRequestManager requests() {
        return requestManager;
    }

    public BedrockFormService forms() {
        return formService;
    }

    public JavaMenuService javaMenus() {
        return javaMenuService;
    }

    public MemberBookService memberBook() {
        return memberBookService;
    }

    public MenuConfigService menus() {
        return menuConfigService;
    }

    public MenuActionService menuActions() { return menuActionService; }

    public EssentialsHomeService homes() {
        return essentialsHomeService;
    }

    public ReportService reports() {
        return reportService;
    }

    public PreferenceService preferences() {
        return preferenceService;
    }

    public AdminMenuEditorService menuEditor() {
        return adminMenuEditorService;
    }

    public FirstJoinTutorialService tutorial() {
        return tutorialService;
    }

    public NamespacedKey playerKey() {
        return playerKey;
    }

    public NamespacedKey buttonKey() {
        return buttonKey;
    }

    public void executeMenuCommand(Player player, MenuButton button) {
        if (!menuConfigService.canUse(player, button)) {
            message(player, "no-permission");
            return;
        }
        if (!menuConfigService.isAvailable(player, button)) {
            message(player, "feature-unavailable");
            return;
        }
        String command = button.command();
        if (command == null || command.isBlank()) {
            message(player, "action-disabled");
            return;
        }

        command = command
                .replace("%player%", player.getName())
                .replace("%uuid%", player.getUniqueId().toString())
                .replace("%world%", player.getWorld().getName());
        dispatchCommand(player, command, button.executor());
    }

    public void dispatchActionCommand(Player player, String template, String executor) {
        if (template == null || template.isBlank()) { message(player, "action-disabled"); return; }
        String command = template.replace("%player%", player.getName()).replace("%uuid%", player.getUniqueId().toString()).replace("%world%", player.getWorld().getName());
        dispatchCommand(player, command, executor);
    }

    public void dispatchPlayerTemplate(Player player, String template, Map<String, String> placeholders) {
        if (template == null || template.isBlank()) {
            message(player, "action-disabled");
            return;
        }
        String command = template
                .replace("%player%", player.getName())
                .replace("%uuid%", player.getUniqueId().toString())
                .replace("%world%", player.getWorld().getName());
        for (Map.Entry<String, String> entry : placeholders.entrySet()) {
            command = command.replace(entry.getKey(), entry.getValue());
        }
        dispatchCommand(player, command, "player");
    }

    private void dispatchCommand(Player player, String command, String executor) {
        if (command.startsWith("/")) command = command.substring(1);
        String normalizedExecutor = executor == null ? "player" : executor.trim();
        if (normalizedExecutor.equalsIgnoreCase("console")) {
            Bukkit.dispatchCommand(Bukkit.getConsoleSender(), command);
        } else {
            player.performCommand(command);
        }
    }

    public String formatMenuText(String value, Player player) {
        if (value == null) return "";
        return Colors.legacy(value
                .replace("%player%", player.getName())
                .replace("%world%", player.getWorld().getName()));
    }

    public void message(Player player, String key, String... replacements) {
        String prefix = getConfig().getString("prefix", "&8[&dCdrMemberBook&8] &r");
        String raw = getConfig().getString("messages." + key, "&cMissing message: " + key);
        if (raw == null) raw = "";
        for (int i = 0; i + 1 < replacements.length; i += 2) {
            raw = raw.replace(replacements[i], replacements[i + 1]);
        }
        player.sendMessage(Colors.legacy((prefix == null ? "" : prefix) + raw));
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        requestManager.removeRequestsFor(event.getPlayer().getUniqueId());
        if (menuActionService != null) menuActionService.cancel(event.getPlayer().getUniqueId());
    }

    @EventHandler
    public void onWorldChange(PlayerChangedWorldEvent event) {
        requestManager.handleWorldChange(event.getPlayer());
    }
}
