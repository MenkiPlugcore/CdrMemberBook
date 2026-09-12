from pathlib import Path

root = Path('.')

def read(path):
    return (root / path).read_text()

def write(path, content):
    (root / path).write_text(content)

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)

# Versions
p = 'pom.xml'
s = read(p)
s = replace_once(s, '<version>1.9.3</version>', '<version>1.9.4</version>', 'pom version')
write(p, s)

p = 'src/main/resources/plugin.yml'
s = read(p)
s = replace_once(s, "version: '1.9.3'", "version: '1.9.4'", 'plugin version')
write(p, s)

# Menu holder: add generic report-center state without breaking existing constructors.
write('src/main/java/id/cadera/memberbook/gui/MenuHolder.java', r'''package id.cadera.memberbook.gui;

import org.bukkit.Bukkit;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.jetbrains.annotations.NotNull;

import java.util.UUID;

public final class MenuHolder implements InventoryHolder {
    public enum Type {
        CONFIG,
        PLAYER_SELECT,
        TP_MODE,
        REPORT_CENTER,
        REPORT_LIST,
        REPORT_DETAIL,
        REPORT_CONFIRM
    }

    private final Type type;
    private final UUID targetId;
    private final String menuId;
    private final int page;
    private final String context;
    private final int value;
    private final Inventory inventory;

    public MenuHolder(Type type, UUID targetId, String menuId, int page, int size, String title) {
        this(type, targetId, menuId, page, "", 0, size, title);
    }

    public MenuHolder(Type type, UUID targetId, String menuId, int page,
                      String context, int value, int size, String title) {
        this.type = type;
        this.targetId = targetId;
        this.menuId = menuId == null ? "main" : menuId;
        this.page = Math.max(0, page);
        this.context = context == null ? "" : context;
        this.value = value;
        this.inventory = Bukkit.createInventory(this, size, title);
    }

    public Type type() { return type; }
    public UUID targetId() { return targetId; }
    public String menuId() { return menuId; }
    public int page() { return page; }
    public String context() { return context; }
    public int value() { return value; }

    @Override
    public @NotNull Inventory getInventory() { return inventory; }
}
''')

# Full Java GUI refresh + Java Report Center.
write('src/main/java/id/cadera/memberbook/gui/JavaMenuService.java', r'''package id.cadera.memberbook.gui;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.menu.MenuConfigService.MenuButton;
import id.cadera.memberbook.menu.MenuConfigService.MenuDefinition;
import id.cadera.memberbook.report.ReportService;
import id.cadera.memberbook.tp.TeleportMode;
import id.cadera.memberbook.util.Colors;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
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
    private static final String REPORT_PREFIX = "__report:";
    private static final String REPORT_OPEN = "__report_open";
    private static final String REPORT_RESOLVED = "__report_resolved";
    private static final String REPORT_ALL = "__report_all";
    private static final String REPORT_REFRESH = "__report_refresh";
    private static final String REPORT_RESOLVE = "__report_resolve";
    private static final String REPORT_REOPEN = "__report_reopen";
    private static final String REPORT_DELETE = "__report_delete";
    private static final String REPORT_CONFIRM = "__report_confirm";
    private static final String REPORT_CANCEL = "__report_cancel";

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
            case REPORT_CENTER -> handleReportCenterClick(player, holder, clicked);
            case REPORT_LIST -> handleReportListClick(player, holder, clicked);
            case REPORT_DETAIL -> handleReportDetailClick(player, holder, clicked);
            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);
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
            case "homes", "pay", "trade", "report" -> { player.closeInventory(); plugin.executeMenuCommand(player, button); }
            case "teleport" -> showPlayerSelect(player, menu.id(), 0);
            case "report-center" -> showReportCenter(player, menu.id());
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

        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CENTER, null, returnMenuId, 0, 27,
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
        inventory.setItem(22, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Member Menu."));
        player.openInventory(inventory);
    }

    private void handleReportCenterClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        if (REPORT_OPEN.equals(action)) showReportList(player, holder.menuId(), ReportService.Status.OPEN, 0);
        else if (REPORT_RESOLVED.equals(action)) showReportList(player, holder.menuId(), ReportService.Status.RESOLVED, 0);
        else if (REPORT_ALL.equals(action)) showReportList(player, holder.menuId(), null, 0);
        else if (REPORT_REFRESH.equals(action)) showReportCenter(player, holder.menuId());
        else if (NAV_BACK.equals(action)) showConfiguredMenu(player, holder.menuId(), 0);
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
        if (!ensureReportStaff(player, returnMenuId)) return;
        ReportService.ReportEntry entry = plugin.reports().get(reportId);
        if (entry == null) {
            plugin.message(player, "report-not-found", "%id%", Integer.toString(reportId));
            showReportList(player, returnMenuId, filter, page);
            return;
        }
        String filterName = filter == null ? "ALL" : filter.name();
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_DETAIL, null, returnMenuId, page,
                filterName, reportId, 27, trimTitle("§8Report §7• §f#" + reportId));
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));

        List<String> details = new ArrayList<>();
        details.add("&7Status: &f" + entry.status());
        details.add("&7Reporter: &f" + entry.reporterName());
        details.add("&7Target: &f" + entry.targetName());
        details.add("&7Waktu: &f" + entry.createdAt());
        details.add("&7Lokasi: &f" + entry.world() + " " + entry.x() + "," + entry.y() + "," + entry.z());
        details.add("");
        details.add("&7Alasan:");
        details.add("&f" + shorten(entry.reason(), 80));
        if (entry.status() == ReportService.Status.RESOLVED) {
            details.add("");
            details.add("&7Resolved by: &f" + entry.resolvedBy());
            details.add("&7Resolved at: &f" + entry.resolvedAt());
        }
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
        player.openInventory(inventory);
    }

    private void handleReportDetailClick(Player player, MenuHolder holder, ItemStack clicked) {
        if (!ensureReportStaff(player, holder.menuId())) return;
        String action = action(clicked);
        ReportService.Status filter = parseFilter(holder.context());
        if (NAV_BACK.equals(action)) { showReportList(player, holder.menuId(), filter, holder.page()); return; }
        if (REPORT_RESOLVE.equals(action)) showReportConfirm(player, holder.menuId(), filter, holder.page(), holder.value(), "resolve");
        else if (REPORT_REOPEN.equals(action)) showReportConfirm(player, holder.menuId(), filter, holder.page(), holder.value(), "reopen");
        else if (REPORT_DELETE.equals(action)) showReportConfirm(player, holder.menuId(), filter, holder.page(), holder.value(), "delete");
    }

    private void showReportConfirm(Player player, String returnMenuId, ReportService.Status filter, int page,
                                   int reportId, String operation) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        if (plugin.reports().get(reportId) == null) {
            plugin.message(player, "report-not-found", "%id%", Integer.toString(reportId));
            showReportList(player, returnMenuId, filter, page);
            return;
        }
        String filterName = filter == null ? "ALL" : filter.name();
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CONFIRM, null, returnMenuId, page,
                operation + "|" + filterName, reportId, 27, "§8Konfirmasi Report");
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
        String[] parts = holder.context().split("\\|", 2);
        String operation = parts.length > 0 ? parts[0] : "";
        ReportService.Status filter = parts.length > 1 ? parseFilter(parts[1]) : null;
        if (REPORT_CANCEL.equals(action)) {
            showReportDetail(player, holder.menuId(), filter, holder.page(), holder.value());
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
            showReportList(player, holder.menuId(), filter, holder.page());
            return;
        }
        switch (operation) {
            case "resolve" -> plugin.message(player, "report-resolved", "%id%", Integer.toString(holder.value()));
            case "reopen" -> plugin.message(player, "report-reopened", "%id%", Integer.toString(holder.value()));
            case "delete" -> plugin.message(player, "report-deleted", "%id%", Integer.toString(holder.value()));
            default -> { }
        }
        if (operation.equals("delete")) showReportList(player, holder.menuId(), filter, holder.page());
        else showReportDetail(player, holder.menuId(), filter, holder.page(), holder.value());
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
        if (button.lore() != null) for (String line : button.lore()) lore.add(plugin.formatMenuText(line, player));
        if (plugin.getConfig().getBoolean("java-menu.decorations.click-hint", true)) {
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
''')

# Report center is now native on Java as well.
p = 'src/main/java/id/cadera/memberbook/menu/MenuConfigService.java'
s = read(p)
old = '''                if (plugin.forms() == null || !plugin.forms().isBedrock(player))
                    yield new Availability(false,"bedrock-only","Report Center Bedrock only");
                yield new Availability(true,"ok","native-report-center");'''
new = '''                yield new Availability(true,"ok", plugin.forms()!=null && plugin.forms().isBedrock(player)
                        ? "native-report-center-bedrock" : "native-report-center-java");'''
s = replace_once(s, old, new, 'report center availability')
write(p, s)

# Main plugin version + migration.
p = 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = read(p)
s = replace_once(s, 'getLogger().info("CdrMemberBook v1.9.3 enabled.");', 'getLogger().info("CdrMemberBook v1.9.4 enabled.");', 'startup version')
old = '''        if (configVersion < 20) {
            getConfig().set("integrations.report.center.enabled", true);
            getConfig().set("integrations.report.center.page-size", 8);
            getConfig().set("integrations.report.center.allow-delete", true);
        }

        getConfig().set("config-version", 20);'''
new = '''        if (configVersion < 20) {
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

        getConfig().set("config-version", 21);'''
s = replace_once(s, old, new, 'config migration 21')
write(p, s)

# Config header + Java GUI section + report-center platform.
p = 'src/main/resources/config.yml'
s = read(p)
s = replace_once(s, '# CdrMemberBook v1.9.3\nconfig-version: 20', '# CdrMemberBook v1.9.4\nconfig-version: 21', 'config header')
insert_anchor = '''# Fully config-driven member menu.
'''
java_section = '''# Java inventory GUI presentation. /menu on Java opens this native GUI.
java-menu:
  decorations:
    enabled: true
    filler-material: BLACK_STAINED_GLASS_PANE
    accent-material: MAGENTA_STAINED_GLASS_PANE
    click-hint: true

'''
s = replace_once(s, insert_anchor, java_section + insert_anchor, 'java menu section')
s = replace_once(s, '''        conditions:
          platform: BEDROCK
        lore:
        - '&7Kelola laporan OPEN/RESOLVED.'
        - '&7Khusus staff Bedrock.'
''', '''        conditions:
          platform: ANY
        lore:
        - '&7Kelola laporan OPEN/RESOLVED.'
        - '&7Native GUI untuk staff Java/Bedrock.'
''', 'report-center platform')
write(p, s)

# README
p = 'README.md'
s = read(p)
s = replace_once(s, '# CdrMemberBook v1.9.3', '# CdrMemberBook v1.9.4', 'readme version')
s = replace_once(s, '- Java inventory GUI fallback.', '- Polished Java inventory GUI untuk `/menu`, lengkap dengan frame, pagination, player info, dan Smart Menu filtering.\n- Native Java + Bedrock Staff Report Center.', 'readme java gui')
write(p, s)

# Changelog
p = 'CHANGELOG.md'
s = read(p)
entry = '''## 1.9.4 - Java Menu UI & Report Center

- Reworked `/menu` on Java into a polished fixed 6-row inventory layout with frame decorations and centered content slots.
- Added Java menu player info, click hints, consistent Previous/Back/Next navigation and cleaner player picker/TP screens.
- Added configurable Java GUI filler/accent materials without requiring a resource pack.
- Added native Java Staff Report Center with OPEN / RESOLVED / ALL lists, pagination and report details.
- Added Java Resolve, Reopen and Delete confirmations with permission rechecks on every report action.
- Report Center is now available to both Java and Bedrock staff through the same `cdrmemberbook.staff.report` permission.
- Config migrated to version 21; existing Bedrock-only Report Center button is migrated to platform `ANY`.


'''
s = replace_once(s, '# Changelog\n\n', '# Changelog\n\n' + entry, 'changelog')
write(p, s)
