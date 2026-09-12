package id.cadera.memberbook.form;

import org.bukkit.Bukkit;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import org.geysermc.cumulus.form.CustomForm;
import org.geysermc.cumulus.form.ModalForm;
import org.geysermc.cumulus.form.SimpleForm;
import org.geysermc.cumulus.util.FormImage;
import org.geysermc.floodgate.api.FloodgateApi;
import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.integration.EssentialsHomeService;
import id.cadera.memberbook.menu.MenuConfigService.MenuButton;
import id.cadera.memberbook.menu.MenuConfigService.MenuDefinition;
import id.cadera.memberbook.report.ReportService;
import id.cadera.memberbook.tp.TeleportMode;

import java.math.BigDecimal;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

public final class BedrockFormService {
    private static final Pattern HOME_NAME = Pattern.compile("[A-Za-z0-9_-]{1,32}");

    private final CdrMemberBookPlugin plugin;

    public BedrockFormService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    public boolean isBedrock(Player player) {
        try {
            return FloodgateApi.getInstance().isFloodgatePlayer(player.getUniqueId());
        } catch (Throwable ignored) {
            return false;
        }
    }

    public void showMainMenu(Player player) {
        showConfiguredMenu(player, "main");
    }

    public void showFirstJoinTutorial(Player player, Runnable onComplete) {
        if (!player.isOnline()) return;
        showTutorialWelcome(player, onComplete == null ? () -> { } : onComplete);
    }

    private void showTutorialWelcome(Player player, Runnable onComplete) {
        String base = "tutorial.welcome.";
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(plugin.formatMenuText(plugin.getConfig().getString(base + "title", "&d&lCdrMemberBook"), player))
                .content(plugin.formatMenuText(plugin.getConfig().getString(base + "content",
                        "&fSelamat datang! Member Book adalah pusat menu pribadi kamu."), player));
        addButton(builder, plugin.getConfig().getString(base + "button", "Lanjut"), "player", "textures/items/book_written");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (player.isOnline()) showTutorialFeatures(player, onComplete);
        })).build());
    }

    private void showTutorialFeatures(Player player, Runnable onComplete) {
        String base = "tutorial.features.";
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(plugin.formatMenuText(plugin.getConfig().getString(base + "title", "Fitur Member Book"), player))
                .content(plugin.formatMenuText(plugin.getConfig().getString(base + "content",
                        "&fGunakan Member Book untuk Home, TPA, Transfer, Barter, Shop dan fitur server lainnya."), player));
        addButton(builder, plugin.getConfig().getString(base + "button", "Lanjut"), "player", "textures/items/compass_item");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (player.isOnline()) showTutorialReady(player, onComplete);
        })).build());
    }

    private void showTutorialReady(Player player, Runnable onComplete) {
        String base = "tutorial.ready.";
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(plugin.formatMenuText(plugin.getConfig().getString(base + "title", "Siap Bermain"), player))
                .content(plugin.formatMenuText(plugin.getConfig().getString(base + "content",
                        "&fKlik kanan Member Book kapan saja untuk membuka Menu Member."), player));
        addButton(builder, plugin.getConfig().getString(base + "button", "Mulai"), "player", "textures/items/emerald");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!player.isOnline()) return;
            onComplete.run();
            if (plugin.getConfig().getBoolean("tutorial.open-menu-after-complete", true)) {
                showMainMenu(player);
            }
        })).build());
    }

    public void showConfiguredMenu(Player player, String menuId) {
        MenuDefinition menu = plugin.menus().getMenu(menuId);
        if (menu == null) {
            plugin.message(player, "menu-not-found", "%menu%", menuId == null ? "main" : menuId);
            if (!"main".equalsIgnoreCase(menuId)) showMainMenu(player);
            return;
        }

        List<MenuButton> buttons = plugin.menus().visibleButtons(menu, player);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(plugin.formatMenuText(menu.title(), player))
                .content(plugin.formatMenuText(menu.content(), player));

        for (MenuButton button : buttons) {
            addConfiguredButton(builder, plugin.formatMenuText(button.name(), player), button.icon());
        }
        boolean hasBack = !menu.id().equals("main");
        if (hasBack) addButton(builder, "Kembali", "back", "textures/items/arrow");

        int backIndex = buttons.size();
        SimpleForm form = builder.validResultHandler(response -> sync(() -> {
                    if (!player.isOnline()) return;
                    int selected = response.clickedButtonId();
                    if (hasBack && selected == backIndex) {
                        showConfiguredMenu(player, menu.backMenu());
                        return;
                    }
                    if (selected < 0 || selected >= buttons.size()) return;
                    handleConfiguredButton(player, menu, buttons.get(selected));
                }))
                .build();
        send(player, form);
    }

    private void handleConfiguredButton(Player player, MenuDefinition menu, MenuButton button) {
        if (!plugin.menus().canUse(player, button)) {
            plugin.message(player, "no-permission");
            return;
        }
        if (!plugin.menus().isAvailable(player, button)) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, menu.id());
            return;
        }

        if (button.actions() != null && !button.actions().isEmpty()) {
            plugin.menuActions().execute(player, button.actions());
            return;
        }

        switch (button.type().toLowerCase(Locale.ROOT)) {
            case "command" -> plugin.executeMenuCommand(player, button);
            case "teleport" -> showTeleportForm(player, menu.id());
            case "homes" -> showHomesMenu(player, menu.id(), button.command());
            case "pay" -> showPayPlayerSelect(player, menu.id());
            case "trade" -> showTradeMenu(player, menu.id());
            case "report" -> showReportPlayerSelect(player, menu.id());
            case "submenu" -> {
                if (button.submenu() == null || button.submenu().isBlank()) {
                    plugin.message(player, "menu-not-found", "%menu%", button.key());
                    return;
                }
                showConfiguredMenu(player, button.submenu());
            }
            case "close" -> { }
            default -> plugin.message(player, "invalid-button-type", "%type%", button.type());
        }
    }

    private void showHomesMenu(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            plugin.message(player, "home-integration-unavailable");
            if (fallbackCommand != null && !fallbackCommand.isBlank()) player.performCommand(stripSlash(fallbackCommand));
            return;
        }

        List<String> names = sortedHomes(homes.homes(player));
        int limit = homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);
        boolean showRefresh = plugin.getConfig().getBoolean(
                "integrations.essentials-home.show-refresh-button", true);

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Home Manager")
                .content("Home tersimpan: " + names.size() + "/" + limitText
                        + "\nPilih menu home tanpa mengetik command.");

        addButton(builder, names.isEmpty() ? "Teleport Home (BELUM ADA)" : "Teleport Home (" + names.size() + ")",
                "home", "textures/items/ender_pearl");
        addButton(builder, "Set Home", "home-add", "textures/items/bed_red");
        addButton(builder, names.isEmpty() ? "Hapus Home (BELUM ADA)" : "Hapus Home (" + names.size() + ")",
                "delete", "textures/items/barrier");
        if (showRefresh) addButton(builder, "Refresh Home", "refresh", "textures/items/compass_item");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int refreshIndex = showRefresh ? 3 : -1;
        int backIndex = showRefresh ? 4 : 3;
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == 0) {
                showTeleportHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == 1) {
                showSetHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == 2) {
                showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == refreshIndex) {
                plugin.message(player, "home-list-refreshed");
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == backIndex) showConfiguredMenu(player, returnMenuId);
        })).build());
    }

    private void showTeleportHomePicker(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> names = sortedHomes(homes.homes(player));
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Teleport Home")
                .content(names.isEmpty() ? "Kamu belum punya home." : "Pilih home tujuan.");

        for (String name : names) {
            HomePreset preset = presetForOwnedHome(name);
            String label = preset == null ? name : preset.displayName();
            String icon = preset == null ? "textures/items/ender_pearl" : preset.icon();
            addConfiguredButton(builder, plugin.formatMenuText(label, player), icon);
        }
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = names.size();

        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected < 0 || selected >= names.size()) return;
            String home = names.get(selected);
            String command = plugin.getConfig().getString("integrations.essentials-home.teleport-command", "home %home%");
            plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", home));
        })).build());
    }

    private void showSetHomePicker(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> existingHomes = sortedHomes(homes.homes(player));
        int limit = homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);
        List<HomePreset> presets = homePresets(player);

        boolean allowCustom = plugin.getConfig().getBoolean("integrations.essentials-home.allow-custom-name", true);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Set Home")
                .content("Home tersimpan: " + existingHomes.size() + "/" + limitText
                        + "\nPilih preset home. Home yang sudah ada akan ditimpa setelah konfirmasi.");

        for (HomePreset preset : presets) {
            boolean existing = containsHome(existingHomes, preset.name());
            String state = preset.allowed() ? (existing ? "Timpa: " : "Set: ") : "Terkunci: ";
            addConfiguredButton(builder,
                    plugin.formatMenuText(state + preset.displayName(), player),
                    preset.icon());
        }
        if (allowCustom) addButton(builder, "Nama Custom", "home-add", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int customIndex = allowCustom ? presets.size() : -1;
        int backIndex = presets.size() + (allowCustom ? 1 : 0);
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (allowCustom && selected == customIndex) {
                showNewHomeForm(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected < 0 || selected >= presets.size()) return;
            HomePreset preset = presets.get(selected);
            if (!preset.allowed()) {
                plugin.message(player, "home-preset-no-permission", "%home%", preset.name());
                showSetHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            confirmOrSetHome(player, preset.name(), returnMenuId, fallbackCommand);
        })).build());
    }

    private void confirmOrSetHome(Player player, String name, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        if (!canUsePresetName(player, name)) {
            plugin.message(player, "home-preset-no-permission", "%home%", name);
            showSetHomePicker(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> names = homes.homes(player);
        boolean existing = containsHome(names, name);
        int limit = homes.maxHomes(player);
        if (!existing && limit >= 0 && names.size() >= limit) {
            plugin.message(player, "home-limit-reached", "%used%", Integer.toString(names.size()), "%max%", Integer.toString(limit));
            showSetHomePicker(player, returnMenuId, fallbackCommand);
            return;
        }

        if (!existing) {
            performSetHome(player, name, returnMenuId, fallbackCommand);
            return;
        }

        ModalForm form = ModalForm.builder()
                .title("Timpa Home")
                .content("Home '" + name + "' sudah ada. Timpa lokasinya dengan posisi kamu sekarang?")
                .button1("TIMPA")
                .button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (response.clickedFirst()) performSetHome(player, name, returnMenuId, fallbackCommand);
                    else showSetHomePicker(player, returnMenuId, fallbackCommand);
                }))
                .build();
        send(player, form);
    }

    private void performSetHome(Player player, String name, String returnMenuId, String fallbackCommand) {
        String command = plugin.getConfig().getString("integrations.essentials-home.set-command", "sethome %home%");
        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", name));
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            plugin.message(player, "home-set-success", "%home%", name);
            showSetHomePicker(player, returnMenuId, fallbackCommand);
        }, 2L);
    }

    private void showNewHomeForm(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        int used = homes == null ? 0 : homes.homes(player).size();
        int limit = homes == null ? 0 : homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);

        CustomForm form = CustomForm.builder()
                .title("Nama Home Custom")
                .input("Nama Home (" + used + "/" + limitText + ")", "contoh: rumah2", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showSetHomePicker(player, returnMenuId, fallbackCommand)))
                .validResultHandler(response -> sync(() -> {
                    String rawName = response.asInput(0);
                    String name = rawName == null ? "" : rawName.trim();
                    if (!HOME_NAME.matcher(name).matches()) {
                        plugin.message(player, "invalid-home-name");
                        showNewHomeForm(player, returnMenuId, fallbackCommand);
                        return;
                    }
                    confirmOrSetHome(player, name, returnMenuId, fallbackCommand);
                }))
                .build();
        send(player, form);
    }

    private void showDeleteHomePicker(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> names = sortedHomes(homes.homes(player));
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Hapus Home")
                .content(names.isEmpty() ? "Kamu belum punya home." : "Pilih home yang ingin dihapus.");
        for (String name : names) {
            HomePreset preset = presetForOwnedHome(name);
            String label = preset == null ? name : preset.displayName();
            String icon = preset == null ? "textures/items/barrier" : preset.icon();
            addConfiguredButton(builder, plugin.formatMenuText(label, player), icon);
        }
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = names.size();

        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected < 0 || selected >= names.size()) return;
            showDeleteHomeConfirm(player, names.get(selected), returnMenuId, fallbackCommand);
        })).build());
    }

    private void showDeleteHomeConfirm(Player player, String home, String returnMenuId, String fallbackCommand) {
        ModalForm form = ModalForm.builder()
                .title("Hapus Home")
                .content("Yakin ingin menghapus home '" + home + "'?")
                .button1("HAPUS")
                .button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (response.clickedFirst()) {
                        String command = plugin.getConfig().getString("integrations.essentials-home.delete-command", "delhome %home%");
                        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", home));
                        Bukkit.getScheduler().runTaskLater(plugin, () -> {
                            if (!player.isOnline()) return;
                            plugin.message(player, "home-delete-success", "%home%", home);
                            showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                        }, 2L);
                    } else {
                        showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                    }
                }))
                .build();
        send(player, form);
    }

    private List<HomePreset> homePresets(Player player) {
        List<String> names = configuredPresetNames();
        boolean hideLocked = plugin.getConfig().getBoolean(
                "integrations.essentials-home.hide-locked-presets", true);

        return names.stream()
                .map(name -> presetDefinition(name, player))
                .filter(HomePreset::enabled)
                .filter(preset -> preset.allowed() || !hideLocked)
                .toList();
    }

    private List<String> configuredPresetNames() {
        List<String> configured = plugin.getConfig().getStringList("integrations.essentials-home.presets");
        List<String> names = configured.stream()
                .map(String::trim)
                .filter(name -> HOME_NAME.matcher(name).matches())
                .distinct()
                .toList();
        return names.isEmpty() ? List.of("rumah", "base", "farm", "tambang", "shop") : names;
    }

    private HomePreset presetDefinition(String name, Player player) {
        String base = "integrations.essentials-home.preset-details." + name + ".";
        boolean enabled = plugin.getConfig().getBoolean(base + "enabled", true);
        String displayName = plugin.getConfig().getString(base + "display-name", prettyHomeName(name));
        String icon = plugin.getConfig().getString(base + "icon", defaultPresetIcon(name));
        String permission = plugin.getConfig().getString(base + "permission", "");
        if (displayName == null || displayName.isBlank()) displayName = prettyHomeName(name);
        if (icon == null || icon.isBlank()) icon = defaultPresetIcon(name);
        if (permission == null) permission = "";
        boolean allowed = permission.isBlank() || player.hasPermission(permission);
        return new HomePreset(name, displayName, icon, permission, enabled, allowed);
    }

    private HomePreset presetForOwnedHome(String home) {
        if (!plugin.getConfig().getBoolean(
                "integrations.essentials-home.use-display-names-on-owned-homes", true)) return null;
        for (String preset : configuredPresetNames()) {
            if (!preset.equalsIgnoreCase(home)) continue;
            String base = "integrations.essentials-home.preset-details." + preset + ".";
            String displayName = plugin.getConfig().getString(base + "display-name", prettyHomeName(preset));
            String icon = plugin.getConfig().getString(base + "icon", defaultPresetIcon(preset));
            boolean enabled = plugin.getConfig().getBoolean(base + "enabled", true);
            return new HomePreset(preset,
                    displayName == null || displayName.isBlank() ? prettyHomeName(preset) : displayName,
                    icon == null || icon.isBlank() ? defaultPresetIcon(preset) : icon,
                    "", enabled, true);
        }
        return null;
    }

    private boolean canUsePresetName(Player player, String name) {
        for (String preset : configuredPresetNames()) {
            if (!preset.equalsIgnoreCase(name)) continue;
            String permission = plugin.getConfig().getString(
                    "integrations.essentials-home.preset-details." + preset + ".permission", "");
            return permission == null || permission.isBlank() || player.hasPermission(permission);
        }
        return true;
    }

    private String prettyHomeName(String name) {
        if (name == null || name.isBlank()) return "Home";
        return Character.toUpperCase(name.charAt(0)) + name.substring(1);
    }

    private String defaultPresetIcon(String name) {
        return switch (name.toLowerCase(Locale.ROOT)) {
            case "rumah", "home", "base" -> "textures/items/bed_red";
            case "farm", "kebun" -> "textures/items/wheat";
            case "tambang", "mine" -> "textures/items/iron_pickaxe";
            case "shop", "toko" -> "textures/items/emerald";
            default -> "textures/items/ender_pearl";
        };
    }

    private List<String> sortedHomes(List<String> homes) {
        if (!plugin.getConfig().getBoolean("integrations.essentials-home.sort-alphabetically", true)) {
            return List.copyOf(homes);
        }
        return homes.stream().sorted(String.CASE_INSENSITIVE_ORDER).toList();
    }

    private boolean containsHome(List<String> homes, String name) {
        return homes.stream().anyMatch(home -> home.equalsIgnoreCase(name));
    }

    private void showPayPlayerSelect(Player player, String returnMenuId) {
        List<PlayerChoice> choices = onlineTargets(player);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Transfer Uang")
                .content(choices.isEmpty() ? "Tidak ada player lain yang online." : "Pilih player penerima.");

        for (PlayerChoice choice : choices) addButton(builder, choice.name(), "player", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = choices.size();

        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showConfiguredMenu(player, returnMenuId);
                return;
            }
            if (selected < 0 || selected >= choices.size()) return;
            Player target = Bukkit.getPlayer(choices.get(selected).uuid());
            if (target == null) {
                plugin.message(player, "player-not-found");
                showPayPlayerSelect(player, returnMenuId);
                return;
            }
            showPayAmountForm(player, target, returnMenuId);
        })).build());
    }

    private void showPayAmountForm(Player player, Player target, String returnMenuId) {
        CustomForm form = CustomForm.builder()
                .title("Transfer ke " + target.getName())
                .input("Nominal", "contoh: 10000", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showPayPlayerSelect(player, returnMenuId)))
                .validResultHandler(response -> sync(() -> {
                    String raw = response.asInput(0);
                    BigDecimal amount = parseAmount(raw);
                    if (amount == null || amount.signum() <= 0) {
                        plugin.message(player, "invalid-pay-amount");
                        showPayAmountForm(player, target, returnMenuId);
                        return;
                    }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) {
                        plugin.message(player, "player-not-found");
                        showPayPlayerSelect(player, returnMenuId);
                        return;
                    }
                    showPayConfirm(player, currentTarget, amount.stripTrailingZeros().toPlainString(), returnMenuId);
                }))
                .build();
        send(player, form);
    }

    private void showPayConfirm(Player player, Player target, String amount, String returnMenuId) {
        ModalForm form = ModalForm.builder()
                .title("Konfirmasi Transfer")
                .content("Kirim " + amount + " ke " + target.getName() + "?")
                .button1("BAYAR")
                .button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (!response.clickedFirst()) {
                        showPayAmountForm(player, target, returnMenuId);
                        return;
                    }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) {
                        plugin.message(player, "player-not-found");
                        showPayPlayerSelect(player, returnMenuId);
                        return;
                    }
                    String command = plugin.getConfig().getString("integrations.pay.command", "pay %target% %amount%");
                    plugin.dispatchPlayerTemplate(player, command, Map.of("%target%", currentTarget.getName(), "%amount%", amount));
                }))
                .build();
        send(player, form);
    }

    private void showReportPlayerSelect(Player player, String returnMenuId) {
        List<PlayerChoice> choices = onlineTargets(player);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Lapor Player")
                .content(choices.isEmpty() ? "Tidak ada player lain yang online." : "Pilih player yang ingin dilaporkan.");
        for (PlayerChoice choice : choices) addButton(builder, choice.name(), "player", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = choices.size();
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showConfiguredMenu(player, returnMenuId);
                return;
            }
            if (selected < 0 || selected >= choices.size()) return;
            Player target = Bukkit.getPlayer(choices.get(selected).uuid());
            if (target == null) {
                plugin.message(player, "player-not-found");
                showReportPlayerSelect(player, returnMenuId);
                return;
            }
            showReportReasonForm(player, target, returnMenuId);
        })).build());
    }

    private void showReportReasonForm(Player player, Player target, String returnMenuId) {
        CustomForm form = CustomForm.builder()
                .title("Lapor " + target.getName())
                .input("Alasan laporan", "contoh: grief, cheat, toxic", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showReportPlayerSelect(player, returnMenuId)))
                .validResultHandler(response -> sync(() -> {
                    String reason = response.asInput(0);
                    int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
                    if (reason == null || reason.trim().length() < min) {
                        plugin.message(player, "report-reason-too-short", "%min%", Integer.toString(min));
                        showReportReasonForm(player, target, returnMenuId);
                        return;
                    }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) {
                        plugin.message(player, "player-not-found");
                        showReportPlayerSelect(player, returnMenuId);
                        return;
                    }
                    showReportConfirm(player, currentTarget, reason.trim(), returnMenuId);
                }))
                .build();
        send(player, form);
    }

    private void showReportConfirm(Player player, Player target, String reason, String returnMenuId) {
        ModalForm form = ModalForm.builder()
                .title("Konfirmasi Laporan")
                .content("Laporkan " + target.getName() + "?\n\nAlasan: " + reason)
                .button1("KIRIM LAPORAN")
                .button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (!response.clickedFirst()) {
                        showReportReasonForm(player, target, returnMenuId);
                        return;
                    }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) {
                        plugin.message(player, "player-not-found");
                        showReportPlayerSelect(player, returnMenuId);
                        return;
                    }
                    ReportService.SubmitResult result = plugin.reports().submit(player, currentTarget, reason);
                    if (result.success()) {
                        plugin.message(player, "report-sent", "%id%", Integer.toString(result.id()),
                                "%player%", currentTarget.getName());
                        showConfiguredMenu(player, returnMenuId);
                    } else if ("cooldown".equals(result.reasonCode())) {
                        plugin.message(player, "report-cooldown", "%seconds%", Long.toString(result.waitSeconds()));
                        showConfiguredMenu(player, returnMenuId);
                    } else if ("self".equals(result.reasonCode())) {
                        plugin.message(player, "cannot-report-self");
                        showReportPlayerSelect(player, returnMenuId);
                    } else {
                        plugin.message(player, "report-failed");
                        showConfiguredMenu(player, returnMenuId);
                    }
                }))
                .build();
        send(player, form);
    }

    private void showTradeMenu(Player player, String returnMenuId) {
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Barter • AxTrade")
                .content("Kelola trade tanpa perlu mengetik nama player.");
        addButton(builder, "Kirim Permintaan Trade", "trade-send", "textures/items/emerald");
        addButton(builder, "Terima Permintaan", "trade-accept", "textures/items/slimeball");
        addButton(builder, "Tolak Permintaan", "trade-deny", "textures/items/barrier");
        addButton(builder, "Aktif/Nonaktif Permintaan", "toggle", "textures/items/lever");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        send(player, builder.validResultHandler(response -> sync(() -> {
            switch (response.clickedButtonId()) {
                case 0 -> showTradePlayerSelect(player, returnMenuId, TradeAction.SEND);
                case 1 -> showTradePlayerSelect(player, returnMenuId, TradeAction.ACCEPT);
                case 2 -> showTradePlayerSelect(player, returnMenuId, TradeAction.DENY);
                case 3 -> {
                    String command = plugin.getConfig().getString("integrations.axtrade.toggle-command", "axtrade toggle");
                    plugin.dispatchPlayerTemplate(player, command, Map.of());
                    Bukkit.getScheduler().runTaskLater(plugin, () -> {
                        if (player.isOnline()) showTradeMenu(player, returnMenuId);
                    }, 1L);
                }
                case 4 -> showConfiguredMenu(player, returnMenuId);
                default -> { }
            }
        })).build());
    }

    private void showTradePlayerSelect(Player player, String returnMenuId, TradeAction action) {
        List<PlayerChoice> choices = onlineTargets(player);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(switch (action) {
                    case SEND -> "Kirim Trade";
                    case ACCEPT -> "Terima Trade";
                    case DENY -> "Tolak Trade";
                })
                .content(choices.isEmpty() ? "Tidak ada player lain yang online." : "Pilih player.");

        for (PlayerChoice choice : choices) addButton(builder, choice.name(), "player", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = choices.size();

        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showTradeMenu(player, returnMenuId);
                return;
            }
            if (selected < 0 || selected >= choices.size()) return;
            Player target = Bukkit.getPlayer(choices.get(selected).uuid());
            if (target == null) {
                plugin.message(player, "player-not-found");
                showTradePlayerSelect(player, returnMenuId, action);
                return;
            }

            String path = switch (action) {
                case SEND -> "integrations.axtrade.send-command";
                case ACCEPT -> "integrations.axtrade.accept-command";
                case DENY -> "integrations.axtrade.deny-command";
            };
            String fallback = switch (action) {
                case SEND -> "axtrade %target%";
                case ACCEPT -> "axtrade accept %target%";
                case DENY -> "axtrade deny %target%";
            };
            String command = plugin.getConfig().getString(path, fallback);
            plugin.dispatchPlayerTemplate(player, command, Map.of("%target%", target.getName()));
        })).build());
    }

    public void showTeleportForm(Player player) {
        showTeleportForm(player, "main");
    }

    private void showTeleportForm(Player player, String returnMenuId) {
        List<PlayerChoice> choices = onlineTargets(player);

        if (choices.isEmpty()) {
            SimpleForm.Builder empty = SimpleForm.builder()
                    .title("Minta Teleport")
                    .content("Tidak ada player lain yang sedang online.");
            addButton(empty, "Kembali", "back", "textures/items/arrow");
            send(player, empty.validResultHandler(response -> sync(() -> showConfiguredMenu(player, returnMenuId))).build());
            return;
        }

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Minta Teleport")
                .content("Pilih player tujuan.");

        for (PlayerChoice choice : choices) {
            addButton(builder, choice.name(), "player", "textures/items/name_tag");
        }
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int backIndex = choices.size();
        SimpleForm form = builder.validResultHandler(response -> sync(() -> {
                    if (!player.isOnline()) return;
                    int selected = response.clickedButtonId();
                    if (selected == backIndex) {
                        showConfiguredMenu(player, returnMenuId);
                        return;
                    }
                    if (selected < 0 || selected >= choices.size()) return;
                    PlayerChoice choice = choices.get(selected);
                    Player target = Bukkit.getPlayer(choice.uuid());
                    if (target == null) {
                        plugin.message(player, "player-not-found");
                        showTeleportForm(player, returnMenuId);
                        return;
                    }
                    showTeleportMode(player, target, returnMenuId);
                }))
                .build();
        send(player, form);
    }

    private void showTeleportMode(Player player, Player target, String returnMenuId) {
        UUID targetId = target.getUniqueId();
        String targetName = target.getName();
        boolean disabled = plugin.requests().toggles().isDisabled(player.getUniqueId());

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Teleport • " + targetName)
                .content("Pilih jenis permintaan teleport.");
        addButton(builder, "Pergi ke " + targetName, "tpa", "textures/items/ender_pearl");
        addButton(builder, "Bawa " + targetName + " ke saya", "tpahere", "textures/items/lead");
        addButton(builder,
                "Permintaan masuk: " + (disabled ? "NONAKTIF" : "AKTIF"),
                "toggle", "textures/items/lever");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        SimpleForm form = builder.validResultHandler(response -> sync(() -> {
                    if (!player.isOnline()) return;
                    switch (response.clickedButtonId()) {
                        case 0 -> createRequest(player, targetId, TeleportMode.TO_TARGET, returnMenuId);
                        case 1 -> createRequest(player, targetId, TeleportMode.TARGET_TO_REQUESTER, returnMenuId);
                        case 2 -> {
                            boolean nowDisabled = plugin.requests().toggles().toggle(player.getUniqueId());
                            plugin.message(player, nowDisabled ? "toggle-off" : "toggle-on");
                            Player currentTarget = Bukkit.getPlayer(targetId);
                            if (currentTarget != null) showTeleportMode(player, currentTarget, returnMenuId);
                            else showTeleportForm(player, returnMenuId);
                        }
                        case 3 -> showTeleportForm(player, returnMenuId);
                        default -> { }
                    }
                }))
                .build();
        send(player, form);
    }

    private void createRequest(Player player, UUID targetId, TeleportMode mode, String returnMenuId) {
        Player target = Bukkit.getPlayer(targetId);
        if (target == null) {
            plugin.message(player, "player-not-found");
            showTeleportForm(player, returnMenuId);
            return;
        }
        plugin.requests().create(player, target, mode);
    }

    public void showIncomingRequest(Player target, Player requester, TeleportMode mode) {
        String content = mode == TeleportMode.TO_TARGET
                ? requester.getName() + " meminta teleport ke lokasimu."
                : requester.getName() + " meminta kamu teleport ke lokasinya.";

        ModalForm form = ModalForm.builder()
                .title("Permintaan Teleport")
                .content(content)
                .button1("TERIMA")
                .button2("TOLAK")
                .validResultHandler(response -> sync(() -> {
                    if (!target.isOnline()) return;
                    if (response.clickedFirst()) plugin.requests().accept(target);
                    else plugin.requests().deny(target);
                }))
                .build();
        send(target, form);
    }

    private List<PlayerChoice> onlineTargets(Player player) {
        return Bukkit.getOnlinePlayers().stream()
                .filter(other -> !other.getUniqueId().equals(player.getUniqueId()))
                .map(other -> new PlayerChoice(other.getUniqueId(), other.getName()))
                .toList();
    }

    private BigDecimal parseAmount(String raw) {
        if (raw == null) return null;
        String value = raw.trim().replace(" ", "");
        if (value.isEmpty()) return null;

        if (value.matches("\\d{1,3}(\\.\\d{3})+")) {
            value = value.replace(".", "");
        } else if (value.matches("\\d{1,3}(,\\d{3})+")) {
            value = value.replace(",", "");
        } else if (value.indexOf(',') >= 0 && value.indexOf('.') < 0) {
            value = value.replace(',', '.');
        }

        try {
            return new BigDecimal(value);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private String stripSlash(String command) {
        String value = command.trim();
        return value.startsWith("/") ? value.substring(1) : value;
    }

    private void addConfiguredButton(SimpleForm.Builder builder, String text, String path) {
        if (plugin.getConfig().getBoolean("bedrock-icons.enabled", true) && path != null && !path.isBlank()) {
            builder.button(text, FormImage.Type.PATH, path);
            return;
        }
        builder.button(text);
    }

    private void addButton(SimpleForm.Builder builder, String text, String iconKey, String fallbackPath) {
        if (plugin.getConfig().getBoolean("bedrock-icons.enabled", true)) {
            String path = plugin.getConfig().getString("bedrock-icons." + iconKey, fallbackPath);
            if (path != null && !path.isBlank()) {
                builder.button(text, FormImage.Type.PATH, path);
                return;
            }
        }
        builder.button(text);
    }

    private void send(Player player, org.geysermc.cumulus.form.Form form) {
        FloodgateApi.getInstance().sendForm(player.getUniqueId(), form);
    }

    private void sync(Runnable runnable) {
        Bukkit.getScheduler().runTask(plugin, runnable);
    }

    private enum TradeAction { SEND, ACCEPT, DENY }

    private record HomePreset(String name, String displayName, String icon, String permission,
                              boolean enabled, boolean allowed) {}

    private record PlayerChoice(UUID uuid, String name) {}
}
