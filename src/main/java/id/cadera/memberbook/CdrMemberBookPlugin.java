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
import id.cadera.memberbook.command.MenuCommand;
import id.cadera.memberbook.command.TeleportCommands;
import id.cadera.memberbook.form.BedrockFormService;
import id.cadera.memberbook.gui.JavaMenuService;
import id.cadera.memberbook.integration.EssentialsHomeService;
import id.cadera.memberbook.item.MemberBookService;
import id.cadera.memberbook.menu.MenuConfigService;
import id.cadera.memberbook.menu.MenuConfigService.MenuButton;
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
    private EssentialsHomeService essentialsHomeService;
    private FirstJoinTutorialService tutorialService;
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
        ToggleStore toggleStore = new ToggleStore(this);
        requestManager = new TeleportRequestManager(this, toggleStore);
        javaMenuService = new JavaMenuService(this);
        memberBookService = new MemberBookService(this);

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
        Bukkit.getPluginManager().registerEvents(memberBookService, this);
        Bukkit.getPluginManager().registerEvents(tutorialService, this);
        memberBookService.validateConfiguration();
        memberBookService.giveToOnlinePlayers();
        memberBookService.startEnforcement();
        getLogger().info("Member Book mode: " + memberBookService.modeName());
        getLogger().info("CdrMemberBook v1.7.0 enabled.");
    }

    @Override
    public void onDisable() {
        if (memberBookService != null) memberBookService.stopEnforcement();
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

        getConfig().set("config-version", 12);
        saveConfig();
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
        if (formService != null && formService.isBedrock(player)) {
            formService.showMainMenu(player);
        } else {
            javaMenuService.showMain(player);
        }
    }

    public void reloadMoonSignConfig() {
        reloadConfig();
        if (memberBookService != null) {
            memberBookService.validateConfiguration();
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

    public EssentialsHomeService homes() {
        return essentialsHomeService;
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
        String prefix = getConfig().getString("prefix", "&8[&dMOONSIGN&8] &r");
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
    }

    @EventHandler
    public void onWorldChange(PlayerChangedWorldEvent event) {
        requestManager.handleWorldChange(event.getPlayer());
    }
}
