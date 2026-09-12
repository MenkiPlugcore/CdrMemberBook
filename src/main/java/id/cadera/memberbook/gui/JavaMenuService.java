package id.cadera.memberbook.gui;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.menu.MenuConfigService.MenuButton;
import id.cadera.memberbook.menu.MenuConfigService.MenuDefinition;
import id.cadera.memberbook.report.ReportService;
import id.cadera.memberbook.preference.PreferenceService;
import id.cadera.memberbook.tp.TeleportMode;
import id.cadera.memberbook.util.Colors;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryType;
import org.bukkit.event.inventory.PrepareAnvilEvent;
import org.bukkit.inventory.AnvilInventory;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.SkullMeta;
import org.bukkit.persistence.PersistentDataType;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

public final class JavaMenuService implements Listener {
    private static final int[] CONTENT_SLOTS = {
            10,11,12,13,14,15,16,
            19,20,21,22,23,24,25,
            28,29,30,31,32,33,34,
            37,38,39,40,41,42,43
    };
    private static final int PAGE_SIZE = CONTENT_SLOTS.length;
    private static final String NAV_BACK = "__back";
    private static final String NAV_CLOSE = "__close";
    private static final String NAV_PREVIOUS = "__previous";
    private static final String NAV_NEXT = "__next";
    private static final String PREF_SOUNDS = "__pref_sounds";
    private static final String PREF_TUTORIAL = "__pref_tutorial";
    private static final String PREF_TP_NOTIFY = "__pref_tp_notify";
    private static final String PREF_REPORT_NOTIFY = "__pref_report_notify";
    private static final String PREF_MENU_MODE = "__pref_menu_mode";
    private static final String PREF_DEFAULT_MENU = "__pref_default_menu";
    private static final String PREF_DEFAULT_PREFIX = "__pref_default:";
    private static final String PREF_RESET = "__pref_reset";
    private static final String REPORT_PREFIX = "__report:";
    private static final String REPORT_OPEN = "__report_open";
    private static final String REPORT_RESOLVED = "__report_resolved";
    private static final String REPORT_ALL = "__report_all";
    private static final String REPORT_REFRESH = "__report_refresh";
    private static final String REPORT_RECENT = "__report_recent";
    private static final String REPORT_SEARCH_HELP = "__report_search_help";
    private static final String REPORT_CATEGORY_FILTER = "__report_category_filter";
    private static final String REPORT_SEARCH_FIELD_PREFIX = "__report_search_field:";
    private static final String REPORT_FILTER_CATEGORY_PREFIX = "__report_filter_category:";
    private static final String REPORT_NOTE_ADD = "__report_note_add";
    private static final String REPORT_RESOLVE = "__report_resolve";
    private static final String REPORT_REOPEN = "__report_reopen";
    private static final String REPORT_DELETE = "__report_delete";
    private static final String REPORT_CONFIRM = "__report_confirm";
    private static final String REPORT_CANCEL = "__report_cancel";
    private static final String REPORT_SUBMIT_CATEGORY_PREFIX = "__report_submit_category:";
    private static final String REPORT_SUBMIT_SEND = "__report_submit_send";
    private static final String REPORT_SUBMIT_EDIT = "__report_submit_edit";
    private static final String REPORT_SUBMIT_CANCEL = "__report_submit_cancel";

    private final CdrMemberBookPlugin plugin;

    public JavaMenuService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    public void showMain(Player player) {
        showConfiguredMenu(player, "main", 0);
    }

    public void showConfiguredMenu(Player player, String menuId, int requestedPage) {
        MenuDefinition menu = plugin.menus().getMenu(menuId);
        if (menu == null) {
            plugin.message(player, "menu-not-found", "%menu%", menuId == null ? "main" : menuId);
            if (!"main".equalsIgnoreCase(menuId)) showMain(player);
            return;
        }

        List<MenuButton> buttons = plugin.menus().visibleButtons(menu, player);
        int totalPages = Math.max(1, (buttons.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = Math.max(0, Math.min(requestedPage, totalPages - 1));
        int start = page * PAGE_SIZE;
        int end = Math.min(buttons.size(), start + PAGE_SIZE);

        String title = plugin.formatMenuText(menu.title(), player);
        MenuHolder holder = new MenuHolder(MenuHolder.Type.CONFIG, null, menu.id(), page, 54, trimTitle(title));
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, page, totalPages, menu.id().equals("main") ? "Menu Utama" : menu.id());

        int slotIndex = 0;
        for (int i = start; i < end; i++) {
            inventory.setItem(CONTENT_SLOTS[slotIndex++], configuredItem(buttons.get(i), player));
        }

        if (page > 0) inventory.setItem(45, navigationItem(Material.ARROW, "&eHalaman Sebelumnya", NAV_PREVIOUS,
                "&7Kembali ke halaman " + page + "."));
        inventory.setItem(49, navigationItem(menu.id().equals("main") ? Material.BARRIER : Material.OAK_DOOR,
                menu.id().equals("main") ? "&cTutup Menu" : "&eKembali",
                menu.id().equals("main") ? NAV_CLOSE : NAV_BACK,
                menu.id().equals("main") ? "&7Tutup CdrMemberBook." : "&7Kembali ke menu sebelumnya."));
        if (page < totalPages - 1) inventory.setItem(53, navigationItem(Material.ARROW, "&eHalaman Berikutnya", NAV_NEXT,
                "&7Buka halaman " + (page + 2) + "."));

        player.openInventory(inventory);
    }

    public void showPlayerSelect(Player player) {
        showPlayerSelect(player, "main", 0);
    }

    private void showPlayerSelect(Player player, String returnMenuId, int requestedPage) {
        List<? extends Player> players = Bukkit.getOnlinePlayers().stream()
                .filter(other -> !other.getUniqueId().equals(player.getUniqueId()))
                .sorted((a, b) -> a.getName().compareToIgnoreCase(b.getName()))
                .toList();
        if (players.isEmpty()) {
            plugin.message(player, "no-other-players");
            showConfiguredMenu(player, returnMenuId, 0);
            return;
        }

        int totalPages = Math.max(1, (players.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = Math.max(0, Math.min(requestedPage, totalPages - 1));
        int start = page * PAGE_SIZE;
        int end = Math.min(players.size(), start + PAGE_SIZE);

        MenuHolder holder = new MenuHolder(MenuHolder.Type.PLAYER_SELECT, null, returnMenuId, page, 54, "§8CdrMemberBook §7• §bPilih Player");
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, page, totalPages, "Teleport Player");

        int slotIndex = 0;
        for (int i = start; i < end; i++) {
            Player target = players.get(i);
            ItemStack head = new ItemStack(Material.PLAYER_HEAD);
            SkullMeta meta = (SkullMeta) head.getItemMeta();
            meta.setDisplayName(Colors.legacy("&b&l" + target.getName()));
            meta.setLore(List.of(
                    Colors.legacy("&7World: &f" + target.getWorld().getName()),
                    Colors.legacy(""),
                    Colors.legacy("&8» &fKlik untuk memilih player ini.")
            ));
            meta.setOwningPlayer(target);
            meta.getPersistentDataContainer().set(plugin.playerKey(), PersistentDataType.STRING, target.getUniqueId().toString());
            head.setItemMeta(meta);
            inventory.setItem(CONTENT_SLOTS[slotIndex++], head);
        }

        if (page > 0) inventory.setItem(45, navigationItem(Material.ARROW, "&eHalaman Sebelumnya", NAV_PREVIOUS, "&7Lihat player sebelumnya."));
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke menu."));
        if (page < totalPages - 1) inventory.setItem(53, navigationItem(Material.ARROW, "&eHalaman Berikutnya", NAV_NEXT, "&7Lihat player berikutnya."));
        player.openInventory(inventory);
    }

    private void showMode(Player player, Player target, String returnMenuId) {
        MenuHolder holder = new MenuHolder(MenuHolder.Type.TP_MODE, target.getUniqueId(), returnMenuId, 0, 27,
                trimTitle("§8Teleport §7• §b" + target.getName()));
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));
        inventory.setItem(4, playerInfoItem(player, 0, 1, "Teleport"));
        inventory.setItem(10, navigationItem(Material.ARROW, "&eKembali", NAV_BACK, "&7Pilih player lain."));
        inventory.setItem(12, item(Material.ENDER_PEARL, "&bPergi ke " + target.getName(), List.of("&7Kirim permintaan teleport ke target.", "", "&8» &fKlik untuk meminta TP.")));
        inventory.setItem(14, item(Material.LEAD, "&dBawa " + target.getName() + " ke saya", List.of("&7Minta target teleport ke lokasimu.", "", "&8» &fKlik untuk meminta TPHere.")));
        boolean disabled = plugin.requests().toggles().isDisabled(player.getUniqueId());
        inventory.setItem(16, item(disabled ? Material.REDSTONE_BLOCK : Material.LIME_CONCRETE,
                disabled ? "&cIncoming TP: OFF" : "&aIncoming TP: ON",
                List.of("&7Aktif/nonaktifkan permintaan TP masuk.", "", "&8» &fKlik untuk toggle.")));
        player.openInventory(inventory);
    }

    @EventHandler
    public void onClick(InventoryClickEvent event) {
        if (!(event.getInventory().getHolder() instanceof MenuHolder holder)) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player)) return;
        if (event.getClickedInventory() == null || event.getClickedInventory() != event.getInventory()) return;
        ItemStack clicked = event.getCurrentItem();
        if (clicked == null || clicked.getType().isAir()) return;

        switch (holder.type()) {
            case CONFIG -> handleConfiguredClick(player, holder, clicked);
            case PLAYER_SELECT -> handlePlayerSelectClick(player, holder, clicked);
            case TP_MODE -> handleTpMode(player, holder, event.getSlot());
            case SETTINGS -> handleSettingsClick(player, holder, clicked);
            case SETTINGS_DEFAULT_MENU -> handleDefaultMenuClick(player, holder, clicked);
            case REPORT_CENTER -> handleReportCenterClick(player, holder, clicked);
            case REPORT_LIST -> handleReportListClick(player, holder, clicked);
            case REPORT_DETAIL -> handleReportDetailClick(player, holder, clicked);
            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);
            case REPORT_SEARCH_TYPE -> handleReportSearchTypeClick(player, holder, clicked);
            case REPORT_SEARCH_INPUT -> handleReportSearchInputClick(player, holder, event.getSlot());
            case REPORT_CATEGORY_FILTER -> handleReportCategoryFilterClick(player, holder, clicked);
            case REPORT_CUSTOM_LIST -> handleReportCustomListClick(player, holder, clicked);
            case REPORT_NOTE_INPUT -> handleReportNoteInputClick(player, holder, event.getSlot());
            case REPORT_SUBMIT_CATEGORY -> handleReportSubmitCategoryClick(player, holder, clicked);
            case REPORT_SUBMIT_PLAYER -> handleReportSubmitPlayerClick(player, holder, clicked);
            case REPORT_SUBMIT_REASON -> handleReportReasonClick(player, holder, event.getSlot());
            case REPORT_SUBMIT_EVIDENCE -> handleReportEvidenceClick(player, holder, event.getSlot());
            case REPORT_SUBMIT_CONFIRM -> handlePlayerReportConfirmClick(player, holder, clicked);
        }
    }

    private void handleConfiguredClick(Player player, MenuHolder holder, ItemStack clicked) {
        String action = action(clicked);
        if (action == null) return;
        if (NAV_CLOSE.equals(action)) { player.closeInventory(); return; }
        if (NAV_PREVIOUS.equals(action)) { showConfiguredMenu(player, holder.menuId(), holder.page() - 1); return; }
        if (NAV_NEXT.equals(action)) { showConfiguredMenu(player, holder.menuId(), holder.page() + 1); return; }

        MenuDefinition menu = plugin.menus().getMenu(holder.menuId());
        if (menu == null) { showMain(player); return; }
        if (NAV_BACK.equals(action)) { showConfiguredMenu(player, menu.backMenu(), 0); return; }

        MenuButton button = plugin.menus().findButton(menu, action);
        if (button == null) return;
        if (!plugin.menus().canUse(player, button)) { plugin.message(player, "no-permission"); return; }
        if (!plugin.menus().isAvailable(player, button)) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, holder.menuId(), holder.page());
            return;
        }

        if (button.actions() != null && !button.actions().isEmpty()) {
            plugin.menuActions().execute(player, button.actions());
            return;
        }

        switch (button.type().toLowerCase(Locale.ROOT)) {
            case "command" -> { player.closeInventory(); plugin.executeMenuCommand(player, button); }
            case "homes", "pay", "trade" -> { player.closeInventory(); plugin.executeMenuCommand(player, button); }
            case "report" -> {
                if (plugin.reports() != null && plugin.reports().enabled()
                        && plugin.getConfig().getBoolean("integrations.report.java-submit.enabled", true)) {
                    showReportCategorySelect(player, menu.id());
                } else {
                    player.closeInventory();
                    plugin.executeMenuCommand(player, button);
                }
            }
            case "teleport" -> showPlayerSelect(player, menu.id(), 0);
            case "report-center" -> showReportCenter(player, menu.id());
            case "settings" -> showSettings(player, menu.id());
            case "submenu" -> {
                if (button.submenu() == null || button.submenu().isBlank()) {
                    plugin.message(player, "menu-not-found", "%menu%", button.key());
                    return;
                }
                showConfiguredMenu(player, button.submenu(), 0);
            }
            case "close" -> player.closeInventory();
            default -> plugin.message(player, "invalid-button-type", "%type%", button.type());
        }
    }

    private void handlePlayerSelectClick(Player player, MenuHolder holder, ItemStack clicked) {
        String nav = action(clicked);
        if (NAV_PREVIOUS.equals(nav)) { showPlayerSelect(player, holder.menuId(), holder.page() - 1); return; }
        if (NAV_NEXT.equals(nav)) { showPlayerSelect(player, holder.menuId(), holder.page() + 1); return; }
        if (NAV_BACK.equals(nav)) { showConfiguredMenu(player, holder.menuId(), 0); return; }

        ItemMeta meta = clicked.getItemMeta();
        String raw = meta.getPersistentDataContainer().get(plugin.playerKey(), PersistentDataType.STRING);
        if (raw == null) return;
        try {
            Player target = Bukkit.getPlayer(UUID.fromString(raw));
            if (target == null) {
                plugin.message(player, "player-not-found");
                showPlayerSelect(player, holder.menuId(), holder.page());
                return;
            }
            showMode(player, target, holder.menuId());
        } catch (IllegalArgumentException ignored) { }
    }

    private void handleTpMode(Player player, MenuHolder holder, int slot) {
        if (slot == 10) { showPlayerSelect(player, holder.menuId(), 0); return; }
        if (slot == 16) {
            boolean disabled = plugin.requests().toggles().toggle(player.getUniqueId());
            plugin.message(player, disabled ? "toggle-off" : "toggle-on");
            Player target = holder.targetId() == null ? null : Bukkit.getPlayer(holder.targetId());
            if (target != null) showMode(player, target, holder.menuId());
            else showPlayerSelect(player, holder.menuId(), 0);
            return;
        }
        if (holder.targetId() == null) return;
        Player target = Bukkit.getPlayer(holder.targetId());
        if (target == null) {
            plugin.message(player, "player-not-found");
            showPlayerSelect(player, holder.menuId(), 0);
            return;
        }
        if (slot == 12) {
            plugin.requests().create(player, target, TeleportMode.TO_TARGET);
            player.closeInventory();
        } else if (slot == 14) {
            plugin.requests().create(player, target, TeleportMode.TARGET_TO_REQUESTER);
            player.closeInventory();
        }
    }

    // ---- Java Native Report Submit ----

    private void showReportCategorySelect(Player player, String returnMenuId) {
        if (plugin.reports() == null || !plugin.reports().enabled()) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, returnMenuId, 0);
            return;
        }
        if (!plugin.reports().categoriesEnabled()) {
            showReportSubmitPlayerSelect(player, returnMenuId, 0, "OTHER");
            return;
        }
        List<String> categories = plugin.reports().categories();
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_CATEGORY, null, returnMenuId, 0, 54,
                "§8Lapor Player §7• §eKategori");
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, 0, 1, "Kategori Laporan");
        int slotIndex = 0;
        for (String category : categories) {
            if (slotIndex >= CONTENT_SLOTS.length) break;
            ItemStack item = navigationItem(Material.BOOK, "&e" + plugin.reports().categoryLabel(category),
                    REPORT_SUBMIT_CATEGORY_PREFIX + category, "&7Kategori: &f" + category + "\n\n&8» &fKlik untuk memilih.");
            inventory.setItem(CONTENT_SLOTS[slotIndex++], item);
        }
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Member Menu."));
        player.openInventory(inventory);
    }

    private void handleReportSubmitCategoryClick(Player player, MenuHolder holder, ItemStack clicked) {
        String action = action(clicked);
        if (NAV_BACK.equals(action)) { showConfiguredMenu(player, holder.menuId(), 0); return; }
        if (action == null || !action.startsWith(REPORT_SUBMIT_CATEGORY_PREFIX)) return;
        String category = plugin.reports().normalizeCategory(action.substring(REPORT_SUBMIT_CATEGORY_PREFIX.length()));
        if (!plugin.reports().categories().contains(category)) { showReportCategorySelect(player, holder.menuId()); return; }
        showReportSubmitPlayerSelect(player, holder.menuId(), 0, category);
    }

    private void showReportSubmitPlayerSelect(Player player, String returnMenuId, int requestedPage, String category) {
        List<? extends Player> players = Bukkit.getOnlinePlayers().stream()
                .filter(other -> !other.getUniqueId().equals(player.getUniqueId()))
                .sorted((a, b) -> a.getName().compareToIgnoreCase(b.getName()))
                .toList();
        if (players.isEmpty()) {
            plugin.message(player, "no-other-players");
            showConfiguredMenu(player, returnMenuId, 0);
            return;
        }
        int totalPages = Math.max(1, (players.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = Math.max(0, Math.min(requestedPage, totalPages - 1));
        int start = page * PAGE_SIZE;
        int end = Math.min(players.size(), start + PAGE_SIZE);
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_PLAYER, null, returnMenuId, page,
                category, 0, 54, "§8Lapor §7• §fPilih Target");
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, page, totalPages, plugin.reports().categoryLabel(category));
        int slotIndex = 0;
        for (int i = start; i < end; i++) {
            Player target = players.get(i);
            ItemStack head = new ItemStack(Material.PLAYER_HEAD);
            SkullMeta meta = (SkullMeta) head.getItemMeta();
            meta.setDisplayName(Colors.legacy("&c&l" + target.getName()));
            meta.setLore(List.of(Colors.legacy("&7Kategori: &f" + plugin.reports().categoryLabel(category)), Colors.legacy(""), Colors.legacy("&8» &fKlik untuk melaporkan.")));
            meta.setOwningPlayer(target);
            meta.getPersistentDataContainer().set(plugin.playerKey(), PersistentDataType.STRING, target.getUniqueId().toString());
            head.setItemMeta(meta);
            inventory.setItem(CONTENT_SLOTS[slotIndex++], head);
        }
        if (page > 0) inventory.setItem(45, navigationItem(Material.ARROW, "&eHalaman Sebelumnya", NAV_PREVIOUS, "&7Lihat player sebelumnya."));
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke kategori."));
        if (page < totalPages - 1) inventory.setItem(53, navigationItem(Material.ARROW, "&eHalaman Berikutnya", NAV_NEXT, "&7Lihat player berikutnya."));
        player.openInventory(inventory);
    }

    private void handleReportSubmitPlayerClick(Player player, MenuHolder holder, ItemStack clicked) {
        String nav = action(clicked);
        String category = plugin.reports().normalizeCategory(holder.context());
        if (NAV_PREVIOUS.equals(nav)) { showReportSubmitPlayerSelect(player, holder.menuId(), holder.page() - 1, category); return; }
        if (NAV_NEXT.equals(nav)) { showReportSubmitPlayerSelect(player, holder.menuId(), holder.page() + 1, category); return; }
        if (NAV_BACK.equals(nav)) { showReportCategorySelect(player, holder.menuId()); return; }
        if (!clicked.hasItemMeta()) return;
        String raw = clicked.getItemMeta().getPersistentDataContainer().get(plugin.playerKey(), PersistentDataType.STRING);
        if (raw == null) return;
        try {
            Player target = Bukkit.getPlayer(UUID.fromString(raw));
            if (target == null) { plugin.message(player, "player-not-found"); showReportSubmitPlayerSelect(player, holder.menuId(), holder.page(), category); return; }
            showReportReasonInput(player, target, holder.menuId(), category);
        } catch (IllegalArgumentException ignored) { }
    }

    private void showReportReasonInput(Player player, Player target, String returnMenuId, String category) {
        if (target == null || !target.isOnline()) { plugin.message(player, "player-not-found"); showReportSubmitPlayerSelect(player, returnMenuId, 0, category); return; }
        String rawTitle = plugin.getConfig().getString("integrations.report.java-submit.reason-title", "&8Lapor • Alasan");
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_REASON, target.getUniqueId(), returnMenuId, 0,
                category, 0, InventoryType.ANVIL, trimTitle(Colors.legacy(rawTitle == null ? "&8Lapor • Alasan" : rawTitle)));
        AnvilInventory inventory = (AnvilInventory) holder.getInventory();
        String placeholder = reportReasonPlaceholder();
        Material material = material(plugin.getConfig().getString("integrations.report.java-submit.reason-material", "PAPER"), Material.PAPER);
        inventory.setItem(0, item(material, "&f" + placeholder, List.of("&7Kategori: &f" + plugin.reports().categoryLabel(category), "&7Target: &f" + target.getName(), "&7Ketik alasan di kolom nama.", "", "&8ESC untuk membatalkan.")));
        inventory.setRepairCost(0);
        player.openInventory(inventory);
    }

    private void showReportEvidenceInput(Player player, Player target, String returnMenuId, String category, String reason) {
        if (!plugin.getConfig().getBoolean("integrations.report.evidence.enabled", true)) { showPlayerReportConfirm(player, target, category, reason, "", returnMenuId); return; }
        if (target == null || !target.isOnline()) { plugin.message(player, "player-not-found"); showReportSubmitPlayerSelect(player, returnMenuId, 0, category); return; }
        String rawTitle = plugin.getConfig().getString("integrations.report.java-submit.evidence-title", "&8Lapor • Evidence");
        String context = category + "\n" + reason;
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_EVIDENCE, target.getUniqueId(), returnMenuId, 0,
                context, 0, InventoryType.ANVIL, trimTitle(Colors.legacy(rawTitle == null ? "&8Lapor • Evidence" : rawTitle)));
        AnvilInventory inventory = (AnvilInventory) holder.getInventory();
        String placeholder = reportEvidencePlaceholder();
        inventory.setItem(0, item(Material.PAPER, "&f" + placeholder, List.of("&7Evidence opsional: teks atau link http/https.", "&7Biarkan placeholder untuk melewati.", "", "&8Klik hasil di kanan untuk lanjut.")));
        inventory.setRepairCost(0);
        player.openInventory(inventory);
    }

    @EventHandler
    public void onPrepareReportAnvil(PrepareAnvilEvent event) {
        if (!(event.getInventory().getHolder() instanceof MenuHolder holder)) return;
        if (holder.type() != MenuHolder.Type.REPORT_SUBMIT_REASON
                && holder.type() != MenuHolder.Type.REPORT_SUBMIT_EVIDENCE
                && holder.type() != MenuHolder.Type.REPORT_SEARCH_INPUT
                && holder.type() != MenuHolder.Type.REPORT_NOTE_INPUT) return;
        AnvilInventory inventory = event.getInventory();
        inventory.setRepairCost(0);
        String value = inventory.getRenameText();
        ItemStack input = inventory.getItem(0);
        if (input == null || input.getType().isAir()) return;
        ItemStack result = input.clone();
        ItemMeta meta = result.getItemMeta();
        String fallback = reportAnvilPlaceholder(holder.type());
        String display = value == null || value.isBlank() ? fallback : value.trim();
        meta.setDisplayName(Colors.legacy("&f" + shorten(display, 48)));
        result.setItemMeta(meta);
        event.setResult(result);
    }

    private void handleReportReasonClick(Player player, MenuHolder holder, int slot) {
        if (slot != 2 || !(holder.getInventory() instanceof AnvilInventory inventory) || holder.targetId() == null) return;
        String category = plugin.reports().normalizeCategory(holder.context());
        Player target = Bukkit.getPlayer(holder.targetId());
        if (target == null) { plugin.message(player, "player-not-found"); showReportSubmitPlayerSelect(player, holder.menuId(), 0, category); return; }
        String reason = inventory.getRenameText();
        if (reason == null) reason = "";
        reason = reason.trim();
        if (reason.equalsIgnoreCase(reportReasonPlaceholder())) reason = "";
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) { plugin.message(player, "report-reason-too-short", "%min%", Integer.toString(min)); showReportReasonInput(player, target, holder.menuId(), category); return; }
        if (reason.length() > max) { plugin.message(player, "report-reason-too-long", "%max%", Integer.toString(max)); showReportReasonInput(player, target, holder.menuId(), category); return; }
        showReportEvidenceInput(player, target, holder.menuId(), category, reason);
    }

    private void handleReportEvidenceClick(Player player, MenuHolder holder, int slot) {
        if (slot != 2 || !(holder.getInventory() instanceof AnvilInventory inventory) || holder.targetId() == null) return;
        String[] draft = holder.context().split("\\n", 2);
        if (draft.length < 2) return;
        String category = plugin.reports().normalizeCategory(draft[0]);
        String reason = draft[1];
        Player target = Bukkit.getPlayer(holder.targetId());
        if (target == null) { plugin.message(player, "player-not-found"); showReportSubmitPlayerSelect(player, holder.menuId(), 0, category); return; }
        String evidence = inventory.getRenameText();
        if (evidence == null) evidence = "";
        evidence = evidence.trim();
        if (evidence.equalsIgnoreCase(reportEvidencePlaceholder())) evidence = "";
        String validation = plugin.reports().validateEvidence(evidence);
        if (!"ok".equals(validation)) { reportEvidenceError(player, validation); showReportEvidenceInput(player, target, holder.menuId(), category, reason); return; }
        showPlayerReportConfirm(player, target, category, reason, evidence, holder.menuId());
    }

    private void showPlayerReportConfirm(Player player, Player target, String category, String reason, String evidence, String returnMenuId) {
        if (target == null || !target.isOnline()) { plugin.message(player, "player-not-found"); showReportSubmitPlayerSelect(player, returnMenuId, 0, category); return; }
        String context = category + "\n" + reason + "\n" + evidence;
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_CONFIRM, target.getUniqueId(), returnMenuId, 0,
                context, 0, 27, trimTitle("§8Konfirmasi §7• §c" + target.getName()));
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));
        ItemStack head = new ItemStack(Material.PLAYER_HEAD);
        SkullMeta headMeta = (SkullMeta) head.getItemMeta();
        headMeta.setOwningPlayer(target);
        headMeta.setDisplayName(Colors.legacy("&c&lLaporkan " + target.getName()));
        List<String> lore = new ArrayList<>();
        lore.add(Colors.legacy("&7Kategori: &f" + plugin.reports().categoryLabel(category)));
        lore.add(Colors.legacy("&7Alasan:"));
        for (String line : wrapText(reason, 36)) lore.add(Colors.legacy("&f" + line));
        lore.add(Colors.legacy("&7Evidence: &f" + (evidence.isBlank() ? "-" : shorten(evidence, 48))));
        headMeta.setLore(lore); head.setItemMeta(headMeta); inventory.setItem(13, head);
        inventory.setItem(10, navigationItem(Material.LIME_CONCRETE, "&a&lKIRIM LAPORAN", REPORT_SUBMIT_SEND, "&7Kirim report ini ke staff."));
        inventory.setItem(16, navigationItem(Material.ANVIL, "&eEdit", REPORT_SUBMIT_EDIT, "&7Kembali ke input alasan."));
        inventory.setItem(22, navigationItem(Material.BARRIER, "&cBatal", REPORT_SUBMIT_CANCEL, "&7Batalkan report."));
        player.openInventory(inventory);
    }

    private void handlePlayerReportConfirmClick(Player player, MenuHolder holder, ItemStack clicked) {
        String action = action(clicked);
        if (action == null || holder.targetId() == null) return;
        String[] draft = holder.context().split("\\n", 3);
        if (draft.length < 3) return;
        String category = draft[0], reason = draft[1], evidence = draft[2];
        Player target = Bukkit.getPlayer(holder.targetId());
        if (REPORT_SUBMIT_CANCEL.equals(action)) { showConfiguredMenu(player, holder.menuId(), 0); return; }
        if (target == null) { plugin.message(player, "player-not-found"); showReportSubmitPlayerSelect(player, holder.menuId(), 0, category); return; }
        if (REPORT_SUBMIT_EDIT.equals(action)) { showReportReasonInput(player, target, holder.menuId(), category); return; }
        if (!REPORT_SUBMIT_SEND.equals(action)) return;
        ReportService.SubmitResult result = plugin.reports().submit(player, target, category, reason, evidence);
        if (result.success()) { plugin.message(player, "report-sent", "%id%", Integer.toString(result.id()), "%player%", target.getName()); showConfiguredMenu(player, holder.menuId(), 0); }
        else if ("cooldown".equals(result.reasonCode())) { plugin.message(player, "report-cooldown", "%seconds%", Long.toString(result.waitSeconds())); showConfiguredMenu(player, holder.menuId(), 0); }
        else if ("duplicate".equals(result.reasonCode())) { plugin.message(player, "report-duplicate", "%id%", Integer.toString(result.id()), "%seconds%", Long.toString(result.waitSeconds())); showConfiguredMenu(player, holder.menuId(), 0); }
        else if ("short".equals(result.reasonCode())) { plugin.message(player, "report-reason-too-short", "%min%", Integer.toString(Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3)))); showReportReasonInput(player, target, holder.menuId(), category); }
        else if (result.reasonCode().startsWith("evidence")) { reportEvidenceError(player, result.reasonCode()); showReportEvidenceInput(player, target, holder.menuId(), category, reason); }
        else { plugin.message(player, "report-failed"); showConfiguredMenu(player, holder.menuId(), 0); }
    }

    private void reportEvidenceError(Player player, String code) {
        if ("evidence-required".equals(code)) plugin.message(player, "report-evidence-required");
        else if ("evidence-too-long".equals(code)) plugin.message(player, "report-evidence-too-long", "%max%", Integer.toString(Math.max(20, plugin.getConfig().getInt("integrations.report.evidence.max-length", 300))));
        else plugin.message(player, "report-evidence-invalid-link");
    }

    private String reportAnvilPlaceholder(MenuHolder.Type type) {
        return switch (type) {
            case REPORT_SUBMIT_REASON -> reportReasonPlaceholder();
            case REPORT_SUBMIT_EVIDENCE -> reportEvidencePlaceholder();
            case REPORT_SEARCH_INPUT -> reportSearchPlaceholder();
            case REPORT_NOTE_INPUT -> reportNotePlaceholder();
            default -> "Ketik...";
        };
    }

    private String reportSearchPlaceholder() {
        String value = plugin.getConfig().getString("integrations.report.center.java-search-placeholder", "Ketik nama / UUID...");
        return value == null || value.isBlank() ? "Ketik nama / UUID..." : value.trim();
    }

    private String reportNotePlaceholder() {
        String value = plugin.getConfig().getString("integrations.report.center.java-note-placeholder", "Ketik catatan staff...");
        return value == null || value.isBlank() ? "Ketik catatan staff..." : value.trim();
    }

    private String reportReasonPlaceholder() {
        String value = plugin.getConfig().getString("integrations.report.java-submit.reason-placeholder", "Ketik alasan laporan...");
        return value == null || value.isBlank() ? "Ketik alasan laporan..." : value.trim();
    }

    private String reportEvidencePlaceholder() {
        String value = plugin.getConfig().getString("integrations.report.java-submit.evidence-placeholder", "Evidence opsional...");
        return value == null || value.isBlank() ? "Evidence opsional..." : value.trim();
    }

    private List<String> wrapText(String value, int width) {
        if (value == null || value.isBlank()) return List.of("");
        int safeWidth = Math.max(12, width);
        List<String> lines = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (String word : value.trim().split("\\s+")) {
            if (current.length() > 0 && current.length() + 1 + word.length() > safeWidth) { lines.add(current.toString()); current.setLength(0); }
            if (current.length() > 0) current.append(' ');
            current.append(word);
        }
        if (current.length() > 0) lines.add(current.toString());
        return lines.isEmpty() ? List.of(value) : List.copyOf(lines);
    }

    // ---- Player Preferences ----

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

    // ---- Java Staff Report Center ----

    private boolean canManageReports(Player player) {
        if (player == null || !player.isOnline()) return false;
        if (!plugin.getConfig().getBoolean("integrations.report.center.enabled", true)) return false;
        String permission = plugin.getConfig().getString("integrations.report.staff-permission", "cdrmemberbook.staff.report");
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }

    private boolean ensureReportStaff(Player player, String returnMenuId) {
        if (canManageReports(player)) return true;
        plugin.message(player, "no-permission");
        if (player.isOnline()) showConfiguredMenu(player, returnMenuId == null ? "main" : returnMenuId, 0);
        return false;
    }

    private void showReportCenter(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        int open = plugin.reports().count(ReportService.Status.OPEN);
        int resolved = plugin.reports().count(ReportService.Status.RESOLVED);
        int all = open + resolved;

        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CENTER, null, returnMenuId, 0, 36,
                "§8CdrMemberBook §7• §cReports");
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));
        inventory.setItem(4, item(Material.WRITTEN_BOOK, "&c&lReport Center", List.of(
                "&7OPEN: &f" + open,
                "&7RESOLVED: &f" + resolved,
                "&7TOTAL: &f" + all
        )));
        inventory.setItem(10, navigationItem(Material.WRITABLE_BOOK, "&cOpen Reports &7(" + open + ")", REPORT_OPEN, "&7Lihat laporan yang masih aktif."));
        inventory.setItem(12, navigationItem(Material.WRITTEN_BOOK, "&aResolved Reports &7(" + resolved + ")", REPORT_RESOLVED, "&7Lihat laporan yang sudah selesai."));
        inventory.setItem(14, navigationItem(Material.BOOK, "&fSemua Reports &7(" + all + ")", REPORT_ALL, "&7Lihat seluruh laporan."));
        inventory.setItem(16, navigationItem(Material.COMPASS, "&bRefresh", REPORT_REFRESH, "&7Perbarui jumlah laporan."));
        if (plugin.getConfig().getBoolean("integrations.report.center.show-recent", true)) {
            inventory.setItem(20, navigationItem(Material.CLOCK, "&eRecent Reports", REPORT_RECENT, "&7Lihat report terbaru."));
        }
        if (plugin.getConfig().getBoolean("integrations.report.center.show-search", true)) {
            inventory.setItem(22, navigationItem(Material.NAME_TAG, "&bCari Report", REPORT_SEARCH_HELP,
                    "&7Cari reporter / target langsung dari GUI."));
        }
        if (plugin.getConfig().getBoolean("integrations.report.center.show-category-filter", true)
                && plugin.reports().categoriesEnabled()) {
            inventory.setItem(24, navigationItem(Material.HOPPER, "&eFilter Kategori", REPORT_CATEGORY_FILTER,
                    "&7Filter report berdasarkan kategori."));
        }
        inventory.setItem(31, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Member Menu."));
        player.openInventory(inventory);
    }

    private void showRecentReportList(Player player, String returnMenuId) {
        showReportCustomList(player, returnMenuId, "RECENT", 0);
    }

    private void handleReportCenterClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        if (REPORT_OPEN.equals(action)) showReportList(player, holder.menuId(), ReportService.Status.OPEN, 0);
        else if (REPORT_RESOLVED.equals(action)) showReportList(player, holder.menuId(), ReportService.Status.RESOLVED, 0);
        else if (REPORT_ALL.equals(action)) showReportList(player, holder.menuId(), null, 0);
        else if (REPORT_RECENT.equals(action)) showRecentReportList(player, holder.menuId());
        else if (REPORT_SEARCH_HELP.equals(action)) showReportSearchType(player, holder.menuId());
        else if (REPORT_CATEGORY_FILTER.equals(action)) showReportCategoryFilter(player, holder.menuId());
        else if (REPORT_REFRESH.equals(action)) showReportCenter(player, holder.menuId());
        else if (NAV_BACK.equals(action)) showConfiguredMenu(player, holder.menuId(), 0);
    }

    private void showReportSearchType(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SEARCH_TYPE, null, returnMenuId, 0, 27,
                "§8Reports §7• §bSearch");
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));
        inventory.setItem(11, navigationItem(Material.PLAYER_HEAD, "&bCari Reporter",
                REPORT_SEARCH_FIELD_PREFIX + ReportService.SearchField.REPORTER.name(), "&7Cari report berdasarkan pengirim laporan."));
        inventory.setItem(13, navigationItem(Material.TARGET, "&cCari Target",
                REPORT_SEARCH_FIELD_PREFIX + ReportService.SearchField.TARGET.name(), "&7Cari report berdasarkan player yang dilaporkan."));
        inventory.setItem(15, navigationItem(Material.COMPASS, "&fCari Keduanya",
                REPORT_SEARCH_FIELD_PREFIX + ReportService.SearchField.ANY.name(), "&7Cari reporter, target, kategori, atau evidence."));
        inventory.setItem(22, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Report Center."));
        player.openInventory(inventory);
    }

    private void handleReportSearchTypeClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        if (NAV_BACK.equals(action)) { showReportCenter(player, holder.menuId()); return; }
        if (action == null || !action.startsWith(REPORT_SEARCH_FIELD_PREFIX)) return;
        try {
            ReportService.SearchField field = ReportService.SearchField.valueOf(action.substring(REPORT_SEARCH_FIELD_PREFIX.length()));
            showReportSearchInput(player, holder.menuId(), field);
        } catch (IllegalArgumentException ignored) { showReportSearchType(player, holder.menuId()); }
    }

    private void showReportSearchInput(Player player, String returnMenuId, ReportService.SearchField field) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        String rawTitle = plugin.getConfig().getString("integrations.report.center.java-search-title", "&8Reports • Search");
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SEARCH_INPUT, null, returnMenuId, 0,
                field.name(), 0, InventoryType.ANVIL, trimTitle(Colors.legacy(rawTitle == null ? "&8Reports • Search" : rawTitle)));
        AnvilInventory inventory = (AnvilInventory) holder.getInventory();
        inventory.setItem(0, item(Material.NAME_TAG, "&f" + reportSearchPlaceholder(), List.of(
                "&7Mode: &f" + field.name(),
                "&7Ketik nama atau UUID player.",
                "&7ANY juga dapat mencari kategori/evidence.",
                "",
                "&8Klik hasil di kanan untuk mencari."
        )));
        inventory.setRepairCost(0);
        player.openInventory(inventory);
    }

    private void handleReportSearchInputClick(Player player, MenuHolder holder, int slot) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        if (slot != 2 || !(holder.getInventory() instanceof AnvilInventory inventory)) return;
        ReportService.SearchField field;
        try { field = ReportService.SearchField.valueOf(holder.context()); }
        catch (IllegalArgumentException ignored) { showReportSearchType(player, holder.menuId()); return; }
        String query = inventory.getRenameText();
        if (query == null) query = "";
        query = query.trim();
        if (query.equalsIgnoreCase(reportSearchPlaceholder())) query = "";
        query = query.replace("|", "").trim();
        if (query.isBlank()) {
            plugin.message(player, "report-search-empty");
            showReportSearchInput(player, holder.menuId(), field);
            return;
        }
        if (query.length() > 64) query = query.substring(0, 64).trim();
        showReportCustomList(player, holder.menuId(), "SEARCH|" + field.name() + "|" + query, 0);
    }

    private void showReportCategoryFilter(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        if (!plugin.reports().categoriesEnabled()) { showReportCenter(player, returnMenuId); return; }
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CATEGORY_FILTER, null, returnMenuId, 0, 54,
                "§8Reports §7• §eKategori");
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, 0, 1, "Filter Kategori");
        int slotIndex = 0;
        for (String category : plugin.reports().categories()) {
            if (slotIndex >= CONTENT_SLOTS.length) break;
            int count = plugin.reports().listByCategory(category, null).size();
            inventory.setItem(CONTENT_SLOTS[slotIndex++], navigationItem(Material.BOOK,
                    "&e" + plugin.reports().categoryLabel(category) + " &7(" + count + ")",
                    REPORT_FILTER_CATEGORY_PREFIX + category,
                    "&7Kategori: &f" + category + "\n&7Total: &f" + count + "\n\n&8» &fKlik untuk filter."));
        }
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eReport Center", NAV_BACK, "&7Kembali ke Report Center."));
        player.openInventory(inventory);
    }

    private void handleReportCategoryFilterClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        if (NAV_BACK.equals(action)) { showReportCenter(player, holder.menuId()); return; }
        if (action == null || !action.startsWith(REPORT_FILTER_CATEGORY_PREFIX)) return;
        String category = plugin.reports().normalizeCategory(action.substring(REPORT_FILTER_CATEGORY_PREFIX.length()));
        if (!plugin.reports().categories().contains(category)) { showReportCategoryFilter(player, holder.menuId()); return; }
        showReportCustomList(player, holder.menuId(), "CATEGORY|" + category, 0);
    }

    private void showReportCustomList(Player player, String returnMenuId, String context, int requestedPage) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        List<ReportService.ReportEntry> entries = customReportEntries(context);
        int configured = Math.max(1, plugin.getConfig().getInt("integrations.report.center.page-size", 8));
        int pageSize = Math.min(PAGE_SIZE, configured);
        int totalPages = Math.max(1, (entries.size() + pageSize - 1) / pageSize);
        int page = Math.max(0, Math.min(requestedPage, totalPages - 1));
        int start = page * pageSize;
        int end = Math.min(entries.size(), start + pageSize);
        String label = listContextLabel(context);

        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CUSTOM_LIST, null, returnMenuId, page,
                context, 0, 54, trimTitle("§8Reports §7• §f" + label));
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, page, totalPages, label);
        int slotIndex = 0;
        for (int i = start; i < end; i++) {
            ReportService.ReportEntry entry = entries.get(i);
            Material material = entry.status() == ReportService.Status.OPEN ? Material.WRITABLE_BOOK : Material.WRITTEN_BOOK;
            ItemStack reportItem = item(material,
                    (entry.status() == ReportService.Status.OPEN ? "&c" : "&a") + "Report #" + entry.id() + " &8• &f" + entry.targetName(),
                    List.of(
                            "&7Kategori: &f" + plugin.reports().categoryLabel(entry.category()),
                            "&7Reporter: &f" + entry.reporterName(),
                            "&7Status: &f" + entry.status(),
                            "&7Alasan: &f" + shorten(entry.reason(), 42),
                            "",
                            "&8» &fKlik untuk detail."
                    ));
            ItemMeta meta = reportItem.getItemMeta();
            meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, REPORT_PREFIX + entry.id());
            reportItem.setItemMeta(meta);
            inventory.setItem(CONTENT_SLOTS[slotIndex++], reportItem);
        }
        if (entries.isEmpty()) inventory.setItem(22, item(Material.PAPER, "&7Tidak ada hasil", List.of("&8Tidak ada report yang cocok.")));
        if (page > 0) inventory.setItem(45, navigationItem(Material.ARROW, "&eHalaman Sebelumnya", NAV_PREVIOUS, "&7Lihat hasil sebelumnya."));
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eReport Center", NAV_BACK, "&7Kembali ke Report Center."));
        if (page < totalPages - 1) inventory.setItem(53, navigationItem(Material.ARROW, "&eHalaman Berikutnya", NAV_NEXT, "&7Lihat hasil berikutnya."));
        player.openInventory(inventory);
    }

    private void handleReportCustomListClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        if (action == null) return;
        if (NAV_PREVIOUS.equals(action)) { showReportCustomList(player, holder.menuId(), holder.context(), holder.page() - 1); return; }
        if (NAV_NEXT.equals(action)) { showReportCustomList(player, holder.menuId(), holder.context(), holder.page() + 1); return; }
        if (NAV_BACK.equals(action)) { showReportCenter(player, holder.menuId()); return; }
        if (action.startsWith(REPORT_PREFIX)) {
            try { showReportDetail(player, holder.menuId(), holder.context(), holder.page(), Integer.parseInt(action.substring(REPORT_PREFIX.length()))); }
            catch (NumberFormatException ignored) { }
        }
    }

    private List<ReportService.ReportEntry> customReportEntries(String context) {
        if (context == null || context.isBlank()) return List.of();
        if (context.equals("RECENT")) {
            int limit = Math.max(1, Math.min(100, plugin.getConfig().getInt("integrations.report.recent-limit", 10)));
            return plugin.reports().recent(limit, null);
        }
        if (context.startsWith("CATEGORY|")) {
            return plugin.reports().listByCategory(context.substring("CATEGORY|".length()), null);
        }
        if (context.startsWith("SEARCH|")) {
            String[] parts = context.split("\\|", 3);
            if (parts.length < 3) return List.of();
            try {
                return plugin.reports().search(parts[2], ReportService.SearchField.valueOf(parts[1]), null);
            } catch (IllegalArgumentException ignored) { return List.of(); }
        }
        return List.of();
    }

    private String statusContext(ReportService.Status filter) {
        return "STATUS|" + (filter == null ? "ALL" : filter.name());
    }

    private String listContextLabel(String context) {
        if (context == null || context.isBlank()) return "ALL";
        if (context.startsWith("STATUS|")) return context.substring("STATUS|".length());
        if (context.equals("RECENT")) return "Recent";
        if (context.startsWith("CATEGORY|")) return plugin.reports().categoryLabel(context.substring("CATEGORY|".length()));
        if (context.startsWith("SEARCH|")) {
            String[] parts = context.split("\\|", 3);
            return parts.length >= 3 ? "Search " + parts[2] : "Search";
        }
        return "Reports";
    }

    private void showReportListContext(Player player, String returnMenuId, String context, int page) {
        if (context != null && (context.equals("RECENT") || context.startsWith("CATEGORY|") || context.startsWith("SEARCH|"))) {
            showReportCustomList(player, returnMenuId, context, page);
            return;
        }
        String raw = context != null && context.startsWith("STATUS|") ? context.substring("STATUS|".length()) : context;
        showReportList(player, returnMenuId, parseFilter(raw), page);
    }

    private void showReportList(Player player, String returnMenuId, ReportService.Status filter, int requestedPage) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        List<ReportService.ReportEntry> entries = plugin.reports().list(filter);
        int configured = Math.max(1, plugin.getConfig().getInt("integrations.report.center.page-size", 8));
        int pageSize = Math.min(PAGE_SIZE, configured);
        int totalPages = Math.max(1, (entries.size() + pageSize - 1) / pageSize);
        int page = Math.max(0, Math.min(requestedPage, totalPages - 1));
        int start = page * pageSize;
        int end = Math.min(entries.size(), start + pageSize);
        String filterName = filter == null ? "ALL" : filter.name();

        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_LIST, null, returnMenuId, page,
                filterName, 0, 54, trimTitle("§8Reports §7• §f" + filterName));
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, page, totalPages, "Reports " + filterName);

        int slotIndex = 0;
        for (int i = start; i < end; i++) {
            ReportService.ReportEntry entry = entries.get(i);
            Material material = entry.status() == ReportService.Status.OPEN ? Material.WRITABLE_BOOK : Material.WRITTEN_BOOK;
            String name = (entry.status() == ReportService.Status.OPEN ? "&c" : "&a") + "Report #" + entry.id() + " &8• &f" + entry.targetName();
            ItemStack item = item(material, name, List.of(
                    "&7Reporter: &f" + entry.reporterName(),
                    "&7Target: &f" + entry.targetName(),
                    "&7Kategori: &f" + plugin.reports().categoryLabel(entry.category()),
                    "&7Status: &f" + entry.status(),
                    "&7Alasan: &f" + shorten(entry.reason(), 42),
                    "",
                    "&8» &fKlik untuk melihat detail."
            ));
            ItemMeta meta = item.getItemMeta();
            meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, REPORT_PREFIX + entry.id());
            item.setItemMeta(meta);
            inventory.setItem(CONTENT_SLOTS[slotIndex++], item);
        }

        if (entries.isEmpty()) inventory.setItem(22, item(Material.PAPER, "&7Belum ada report", List.of("&8Tidak ada report pada filter ini.")));
        if (page > 0) inventory.setItem(45, navigationItem(Material.ARROW, "&eHalaman Sebelumnya", NAV_PREVIOUS, "&7Lihat report sebelumnya."));
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eReport Center", NAV_BACK, "&7Kembali ke Report Center."));
        if (page < totalPages - 1) inventory.setItem(53, navigationItem(Material.ARROW, "&eHalaman Berikutnya", NAV_NEXT, "&7Lihat report berikutnya."));
        player.openInventory(inventory);
    }

    private void handleReportListClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        if (action == null) return;
        ReportService.Status filter = parseFilter(holder.context());
        if (NAV_PREVIOUS.equals(action)) { showReportList(player, holder.menuId(), filter, holder.page() - 1); return; }
        if (NAV_NEXT.equals(action)) { showReportList(player, holder.menuId(), filter, holder.page() + 1); return; }
        if (NAV_BACK.equals(action)) { showReportCenter(player, holder.menuId()); return; }
        if (action.startsWith(REPORT_PREFIX)) {
            try { showReportDetail(player, holder.menuId(), filter, holder.page(), Integer.parseInt(action.substring(REPORT_PREFIX.length()))); }
            catch (NumberFormatException ignored) { }
        }
    }

    private void showReportDetail(Player player, String returnMenuId, ReportService.Status filter, int page, int reportId) {
        showReportDetail(player, returnMenuId, statusContext(filter), page, reportId);
    }

    private void showReportDetail(Player player, String returnMenuId, String listContext, int page, int reportId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        ReportService.ReportEntry entry = plugin.reports().get(reportId);
        if (entry == null) {
            plugin.message(player, "report-not-found", "%id%", Integer.toString(reportId));
            showReportListContext(player, returnMenuId, listContext, page);
            return;
        }
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_DETAIL, null, returnMenuId, page,
                listContext, reportId, 27, trimTitle("§8Report §7• §f#" + reportId));
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));

        List<String> details = new ArrayList<>();
        details.add("&7Status: &f" + entry.status());
        details.add("&7Reporter: &f" + entry.reporterName());
        details.add("&7Target: &f" + entry.targetName());
        details.add("&7Kategori: &f" + plugin.reports().categoryLabel(entry.category()) + " &8(" + entry.category() + ")");
        details.add("&7Total report target: &f" + plugin.reports().countByTarget(entry.targetUuid(), null)
                + " &8(OPEN: &f" + plugin.reports().countByTarget(entry.targetUuid(), ReportService.Status.OPEN) + "&8)");
        details.add("&7Waktu: &f" + entry.createdAt());
        details.add("&7Lokasi: &f" + entry.world() + " " + entry.x() + "," + entry.y() + "," + entry.z());
        details.add("");
        details.add("&7Alasan:");
        details.add("&f" + shorten(entry.reason(), 80));
        details.add("&7Evidence: &f" + (entry.evidence().isBlank() ? "-" : shorten(entry.evidence(), 80)));
        if (entry.status() == ReportService.Status.RESOLVED) {
            details.add("");
            details.add("&7Resolved by: &f" + entry.resolvedBy());
            details.add("&7Resolved at: &f" + entry.resolvedAt());
        }
        if (!entry.notes().isEmpty()) {
            ReportService.StaffNote note = entry.notes().get(entry.notes().size() - 1);
            details.add("");
            details.add("&eLatest note: &f" + shorten(note.text(), 60));
            details.add("&8oleh " + note.staff());
        }
        details.add("&7Audit: &f" + entry.audit().size() + " &8| &7Notes: &f" + entry.notes().size());
        inventory.setItem(13, item(entry.status() == ReportService.Status.OPEN ? Material.WRITABLE_BOOK : Material.WRITTEN_BOOK,
                (entry.status() == ReportService.Status.OPEN ? "&c" : "&a") + "&lReport #" + reportId, details));
        inventory.setItem(10, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke daftar report."));
        inventory.setItem(12, navigationItem(entry.status() == ReportService.Status.OPEN ? Material.EMERALD : Material.COMPASS,
                entry.status() == ReportService.Status.OPEN ? "&aResolve Report" : "&eReopen Report",
                entry.status() == ReportService.Status.OPEN ? REPORT_RESOLVE : REPORT_REOPEN,
                entry.status() == ReportService.Status.OPEN ? "&7Tandai laporan sebagai selesai." : "&7Buka kembali laporan ini."));
        if (plugin.getConfig().getBoolean("integrations.report.center.allow-delete", true)) {
            inventory.setItem(16, navigationItem(Material.BARRIER, "&cHapus Report", REPORT_DELETE, "&7Hapus laporan ini permanen."));
        }
        inventory.setItem(22, navigationItem(Material.PAPER, "&eTambah Staff Note", REPORT_NOTE_ADD,
                "&7Klik untuk menambah catatan staff via Anvil UI.\n&8Audit tetap tersimpan otomatis."));
        player.openInventory(inventory);
    }

    private void handleReportDetailClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        String listContext = holder.context();
        if (NAV_BACK.equals(action)) { showReportListContext(player, holder.menuId(), listContext, holder.page()); return; }
        if (REPORT_RESOLVE.equals(action)) showReportConfirm(player, holder.menuId(), listContext, holder.page(), holder.value(), "resolve");
        else if (REPORT_REOPEN.equals(action)) showReportConfirm(player, holder.menuId(), listContext, holder.page(), holder.value(), "reopen");
        else if (REPORT_DELETE.equals(action)) showReportConfirm(player, holder.menuId(), listContext, holder.page(), holder.value(), "delete");
        else if (REPORT_NOTE_ADD.equals(action)) showReportNoteInput(player, holder.menuId(), listContext, holder.page(), holder.value());
    }

    private void showReportNoteInput(Player player, String returnMenuId, String listContext, int page, int reportId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        if (plugin.reports().get(reportId) == null) {
            plugin.message(player, "report-not-found", "%id%", Integer.toString(reportId));
            showReportListContext(player, returnMenuId, listContext, page);
            return;
        }
        String rawTitle = plugin.getConfig().getString("integrations.report.center.java-note-title", "&8Report • Staff Note");
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_NOTE_INPUT, null, returnMenuId, page,
                listContext, reportId, InventoryType.ANVIL, trimTitle(Colors.legacy(rawTitle == null ? "&8Report • Staff Note" : rawTitle)));
        AnvilInventory inventory = (AnvilInventory) holder.getInventory();
        inventory.setItem(0, item(Material.PAPER, "&f" + reportNotePlaceholder(), List.of(
                "&7Report: &f#" + reportId,
                "&7Ketik catatan internal staff.",
                "&7Catatan masuk ke audit report.",
                "",
                "&8Klik hasil di kanan untuk simpan."
        )));
        inventory.setRepairCost(0);
        player.openInventory(inventory);
    }

    private void handleReportNoteInputClick(Player player, MenuHolder holder, int slot) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        if (slot != 2 || !(holder.getInventory() instanceof AnvilInventory inventory)) return;
        String note = inventory.getRenameText();
        if (note == null) note = "";
        note = note.trim();
        if (note.equalsIgnoreCase(reportNotePlaceholder())) note = "";
        if (note.isBlank()) {
            showReportDetail(player, holder.menuId(), holder.context(), holder.page(), holder.value());
            return;
        }
        int max = Math.max(10, plugin.getConfig().getInt("integrations.report.audit.max-note-length", 240));
        if (note.length() > max) {
            plugin.message(player, "report-note-too-long", "%max%", Integer.toString(max));
            showReportNoteInput(player, holder.menuId(), holder.context(), holder.page(), holder.value());
            return;
        }
        if (!plugin.reports().addNote(holder.value(), player.getName(), note)) {
            plugin.message(player, "report-action-failed");
            showReportDetail(player, holder.menuId(), holder.context(), holder.page(), holder.value());
            return;
        }
        plugin.message(player, "report-note-added", "%id%", Integer.toString(holder.value()));
        showReportDetail(player, holder.menuId(), holder.context(), holder.page(), holder.value());
    }

    private void showReportConfirm(Player player, String returnMenuId, String listContext, int page,
                                   int reportId, String operation) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        if (plugin.reports().get(reportId) == null) {
            plugin.message(player, "report-not-found", "%id%", Integer.toString(reportId));
            showReportListContext(player, returnMenuId, listContext, page);
            return;
        }
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CONFIRM, null, returnMenuId, page,
                operation + "\n" + listContext, reportId, 27, "§8Konfirmasi Report");
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));
        String label = switch (operation) {
            case "resolve" -> "Resolve report #" + reportId + "?";
            case "reopen" -> "Reopen report #" + reportId + "?";
            case "delete" -> "Hapus permanen report #" + reportId + "?";
            default -> "Konfirmasi report #" + reportId + "?";
        };
        inventory.setItem(4, item(Material.PAPER, "&f&l" + label, List.of("&7Pastikan tindakan ini memang diinginkan.")));
        inventory.setItem(11, navigationItem(operation.equals("delete") ? Material.RED_CONCRETE : Material.LIME_CONCRETE,
                operation.equals("delete") ? "&c&lHAPUS" : "&a&lKONFIRMASI", REPORT_CONFIRM, "&7Klik untuk melanjutkan."));
        inventory.setItem(15, navigationItem(Material.GRAY_CONCRETE, "&7BATAL", REPORT_CANCEL, "&7Kembali tanpa perubahan."));
        player.openInventory(inventory);
    }

    private void handleReportConfirmClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        String[] parts = holder.context().split("\\n", 2);
        String operation = parts.length > 0 ? parts[0] : "";
        String listContext = parts.length > 1 ? parts[1] : statusContext(null);
        if (REPORT_CANCEL.equals(action)) {
            showReportDetail(player, holder.menuId(), listContext, holder.page(), holder.value());
            return;
        }
        if (!REPORT_CONFIRM.equals(action)) return;
        boolean success = switch (operation) {
            case "resolve" -> plugin.reports().resolve(holder.value(), player.getName());
            case "reopen" -> plugin.reports().reopen(holder.value(), player.getName());
            case "delete" -> plugin.reports().delete(holder.value());
            default -> false;
        };
        if (!success) {
            plugin.message(player, "report-action-failed");
            showReportListContext(player, holder.menuId(), listContext, holder.page());
            return;
        }
        switch (operation) {
            case "resolve" -> plugin.message(player, "report-resolved", "%id%", Integer.toString(holder.value()));
            case "reopen" -> plugin.message(player, "report-reopened", "%id%", Integer.toString(holder.value()));
            case "delete" -> plugin.message(player, "report-deleted", "%id%", Integer.toString(holder.value()));
            default -> { }
        }
        if (operation.equals("delete")) showReportListContext(player, holder.menuId(), listContext, holder.page());
        else showReportDetail(player, holder.menuId(), listContext, holder.page(), holder.value());
    }

    private ReportService.Status parseFilter(String raw) {
        if (raw == null || raw.isBlank() || raw.equalsIgnoreCase("ALL")) return null;
        try { return ReportService.Status.valueOf(raw.toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ignored) { return null; }
    }

    // ---- Visual helpers ----

    private void decorateFrame(Inventory inventory, Player player, int page, int totalPages, String section) {
        if (!plugin.getConfig().getBoolean("java-menu.decorations.enabled", true)) return;
        Material fillerMat = material(plugin.getConfig().getString("java-menu.decorations.filler-material", "BLACK_STAINED_GLASS_PANE"), Material.BLACK_STAINED_GLASS_PANE);
        Material accentMat = material(plugin.getConfig().getString("java-menu.decorations.accent-material", "MAGENTA_STAINED_GLASS_PANE"), Material.MAGENTA_STAINED_GLASS_PANE);
        ItemStack filler = filler(fillerMat);
        ItemStack accent = filler(accentMat);
        fillAll(inventory, filler);
        for (int i = 0; i < 9; i++) inventory.setItem(i, accent);
        for (int i = 45; i < 54; i++) inventory.setItem(i, filler);
        inventory.setItem(4, playerInfoItem(player, page, totalPages, section));
    }

    private ItemStack playerInfoItem(Player player, int page, int totalPages, String section) {
        ItemStack head = new ItemStack(Material.PLAYER_HEAD);
        SkullMeta meta = (SkullMeta) head.getItemMeta();
        meta.setOwningPlayer(player);
        meta.setDisplayName(Colors.legacy("&d&l" + player.getName()));
        meta.setLore(List.of(
                Colors.legacy("&7Menu: &f" + section),
                Colors.legacy("&7World: &f" + player.getWorld().getName()),
                Colors.legacy("&7Online: &f" + Bukkit.getOnlinePlayers().size()),
                Colors.legacy("&7Halaman: &f" + (page + 1) + "/" + totalPages)
        ));
        head.setItemMeta(meta);
        return head;
    }

    private ItemStack configuredItem(MenuButton button, Player player) {
        Material material = Material.matchMaterial(button.javaMaterial() == null ? "PAPER" : button.javaMaterial());
        if (material == null || material.isAir()) material = Material.PAPER;
        ItemStack item = new ItemStack(material);
        ItemMeta meta = item.getItemMeta();
        meta.setDisplayName(plugin.formatMenuText(button.name(), player));
        List<String> lore = new ArrayList<>();
        boolean compact = plugin.preferences() != null && plugin.preferences().compact(player);
        if (!compact && button.lore() != null) for (String line : button.lore()) lore.add(plugin.formatMenuText(line, player));
        if (!compact && plugin.getConfig().getBoolean("java-menu.decorations.click-hint", true)) {
            if (!lore.isEmpty()) lore.add("");
            lore.add(Colors.legacy("&8» &fKlik untuk membuka."));
        }
        if (!lore.isEmpty()) meta.setLore(lore);
        meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, button.key());
        item.setItemMeta(meta);
        return item;
    }

    private String action(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return null;
        return item.getItemMeta().getPersistentDataContainer().get(plugin.buttonKey(), PersistentDataType.STRING);
    }

    private ItemStack navigationItem(Material material, String name, String action, String lore) {
        ItemStack item = item(material, name, lore == null || lore.isBlank() ? List.of() : List.of(lore));
        ItemMeta meta = item.getItemMeta();
        meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, action);
        item.setItemMeta(meta);
        return item;
    }

    private ItemStack item(Material material, String name, List<String> loreLines) {
        ItemStack item = new ItemStack(material);
        ItemMeta meta = item.getItemMeta();
        meta.setDisplayName(Colors.legacy(name));
        if (loreLines != null && !loreLines.isEmpty()) {
            List<String> lore = new ArrayList<>();
            for (String line : loreLines) lore.add(Colors.legacy(line));
            meta.setLore(lore);
        }
        item.setItemMeta(meta);
        return item;
    }

    private ItemStack filler(Material material) {
        return item(material, " ", List.of());
    }

    private void fillAll(Inventory inventory, ItemStack item) {
        for (int i = 0; i < inventory.getSize(); i++) inventory.setItem(i, item.clone());
    }

    private Material material(String raw, Material fallback) {
        Material found = raw == null ? null : Material.matchMaterial(raw);
        return found == null || found.isAir() ? fallback : found;
    }

    private String shorten(String value, int max) {
        if (value == null) return "";
        return value.length() <= max ? value : value.substring(0, Math.max(0, max - 3)) + "...";
    }

    private String trimTitle(String title) {
        if (title == null) return "CdrMemberBook";
        return title.length() <= 32 ? title : title.substring(0, 32);
    }
}
