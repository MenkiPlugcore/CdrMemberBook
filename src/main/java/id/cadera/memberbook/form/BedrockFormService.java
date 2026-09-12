package id.cadera.memberbook.form;

import org.bukkit.Bukkit;
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

        switch (button.type().toLowerCase(Locale.ROOT)) {
            case "command" -> plugin.executeMenuCommand(player, button);
            case "teleport" -> showTeleportForm(player, menu.id());
            case "homes" -> showHomesMenu(player, menu.id(), button.command());
            case "pay" -> showPayPlayerSelect(player, menu.id());
            case "trade" -> showTradeMenu(player, menu.id());
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

        List<String> names = homes.homes(player);
        int limit = homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Home Manager")
                .content("Home tersimpan: " + names.size() + "/" + limitText + "\nPilih home untuk teleport atau hapus.");

        String addLabel = limit >= 0 && names.size() >= limit ? "Set Home Baru (PENUH)" : "Set Home Baru";
        addButton(builder, addLabel, "home-add", "textures/items/bed_red");
        for (String name : names) addButton(builder, name, "home", "textures/items/bed_red");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int backIndex = names.size() + 1;
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == 0) {
                if (limit >= 0 && names.size() >= limit) {
                    plugin.message(player, "home-limit-reached", "%used%", Integer.toString(names.size()), "%max%", limitText);
                    showHomesMenu(player, returnMenuId, fallbackCommand);
                } else {
                    showNewHomeForm(player, returnMenuId, fallbackCommand);
                }
                return;
            }
            if (selected == backIndex) {
                showConfiguredMenu(player, returnMenuId);
                return;
            }
            int homeIndex = selected - 1;
            if (homeIndex >= 0 && homeIndex < names.size()) {
                showHomeActions(player, names.get(homeIndex), returnMenuId, fallbackCommand);
            }
        })).build());
    }

    private void showNewHomeForm(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        int used = homes == null ? 0 : homes.homes(player).size();
        int limit = homes == null ? 0 : homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);

        CustomForm form = CustomForm.builder()
                .title("Set Home Baru")
                .input("Nama Home (" + used + "/" + limitText + ")", "contoh: rumah", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showHomesMenu(player, returnMenuId, fallbackCommand)))
                .validResultHandler(response -> sync(() -> {
                    String rawName = response.asInput(0);
                    final String name = rawName == null ? "" : rawName.trim();
                    if (!HOME_NAME.matcher(name).matches()) {
                        plugin.message(player, "invalid-home-name");
                        showNewHomeForm(player, returnMenuId, fallbackCommand);
                        return;
                    }

                    EssentialsHomeService currentHomes = plugin.homes();
                    if (currentHomes != null) {
                        int currentLimit = currentHomes.maxHomes(player);
                        int currentUsed = currentHomes.homes(player).size();
                        boolean existing = currentHomes.homes(player).stream().anyMatch(home -> home.equalsIgnoreCase(name));
                        if (!existing && currentLimit >= 0 && currentUsed >= currentLimit) {
                            plugin.message(player, "home-limit-reached", "%used%", Integer.toString(currentUsed), "%max%", Integer.toString(currentLimit));
                            showHomesMenu(player, returnMenuId, fallbackCommand);
                            return;
                        }
                    }

                    String command = plugin.getConfig().getString("integrations.essentials-home.set-command", "sethome %home%");
                    plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", name));
                    Bukkit.getScheduler().runTaskLater(plugin, () -> {
                        if (player.isOnline()) showHomesMenu(player, returnMenuId, fallbackCommand);
                    }, 2L);
                }))
                .build();
        send(player, form);
    }

    private void showHomeActions(Player player, String home, String returnMenuId, String fallbackCommand) {
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Home • " + home)
                .content("Pilih tindakan untuk home ini.");
        addButton(builder, "Teleport ke " + home, "home", "textures/items/ender_pearl");
        addButton(builder, "Hapus " + home, "delete", "textures/items/barrier");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        send(player, builder.validResultHandler(response -> sync(() -> {
            switch (response.clickedButtonId()) {
                case 0 -> {
                    String command = plugin.getConfig().getString("integrations.essentials-home.teleport-command", "home %home%");
                    plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", home));
                }
                case 1 -> showDeleteHomeConfirm(player, home, returnMenuId, fallbackCommand);
                case 2 -> showHomesMenu(player, returnMenuId, fallbackCommand);
                default -> { }
            }
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
                            if (player.isOnline()) showHomesMenu(player, returnMenuId, fallbackCommand);
                        }, 2L);
                    } else {
                        showHomeActions(player, home, returnMenuId, fallbackCommand);
                    }
                }))
                .build();
        send(player, form);
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

    private record PlayerChoice(UUID uuid, String name) {}
}
