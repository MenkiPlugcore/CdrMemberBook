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

def insert_before(text, marker, block, label):
    if marker not in text:
        raise SystemExit(f'marker not found: {label}')
    return text.replace(marker, block + marker, 1)

# ---- Versions ----
p = 'pom.xml'
s = read(p)
s = replace_once(s, '<version>1.9.7</version>', '<version>1.9.8</version>', 'pom version')
write(p, s)

p = 'src/main/resources/plugin.yml'
s = read(p)
s = replace_once(s, "version: '1.9.7'", "version: '1.9.8'", 'plugin version')
write(p, s)

p = 'src/main/resources/config.yml'
s = read(p)
s = replace_once(s, '# CdrMemberBook v1.9.7\nconfig-version: 24', '# CdrMemberBook v1.9.8\nconfig-version: 25', 'config version')
s = replace_once(s, '''    center:\n      enabled: true\n      page-size: 8\n      allow-delete: true\n      show-recent: true\n      show-search: true\n      detail-note-limit: 3\n      detail-audit-limit: 5\n''', '''    center:\n      enabled: true\n      page-size: 8\n      allow-delete: true\n      show-recent: true\n      show-search: true\n      show-category-filter: true\n      # Java staff QoL: search dan staff-note memakai Anvil UI native.\n      java-search-title: '&8Reports • Search'\n      java-search-placeholder: 'Ketik nama / UUID...'\n      java-note-title: '&8Report • Staff Note'\n      java-note-placeholder: 'Ketik catatan staff...'\n      detail-note-limit: 3\n      detail-audit-limit: 5\n''', 'config report center QoL')
s = replace_once(s, '''  report-note-added: '&aCatatan staff ditambahkan ke report &f#%id%&a.'\n''', '''  report-note-added: '&aCatatan staff ditambahkan ke report &f#%id%&a.'\n  report-note-too-long: '&eCatatan staff maksimal &f%max% &ekarakter.'\n  report-search-empty: '&eMasukkan nama atau UUID untuk mencari report.'\n''', 'config messages')
write(p, s)

# ---- Config migration ----
p = 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = read(p)
block = '''        if (configVersion < 25) {\n            getConfig().set("integrations.report.center.show-category-filter", true);\n            getConfig().set("integrations.report.center.java-search-title", "&8Reports • Search");\n            getConfig().set("integrations.report.center.java-search-placeholder", "Ketik nama / UUID...");\n            getConfig().set("integrations.report.center.java-note-title", "&8Report • Staff Note");\n            getConfig().set("integrations.report.center.java-note-placeholder", "Ketik catatan staff...");\n        }\n\n'''
s = insert_before(s, '        getConfig().set("config-version", 24);\n', block, 'migration v25')
s = replace_once(s, '        getConfig().set("config-version", 24);\n', '        getConfig().set("config-version", 25);\n', 'config version final')
s = s.replace('v1.9.7', 'v1.9.8')
write(p, s)

# ---- Menu holder states ----
p = 'src/main/java/id/cadera/memberbook/gui/MenuHolder.java'
s = read(p)
s = replace_once(s, '''        REPORT_DETAIL,\n        REPORT_CONFIRM,\n        REPORT_SUBMIT_CATEGORY,\n''', '''        REPORT_DETAIL,\n        REPORT_CONFIRM,\n        REPORT_SEARCH_TYPE,\n        REPORT_SEARCH_INPUT,\n        REPORT_CATEGORY_FILTER,\n        REPORT_CUSTOM_LIST,\n        REPORT_NOTE_INPUT,\n        REPORT_SUBMIT_CATEGORY,\n''', 'MenuHolder report QoL states')
write(p, s)

# ---- Java Report Center QoL ----
p = 'src/main/java/id/cadera/memberbook/gui/JavaMenuService.java'
s = read(p)

s = replace_once(s, '''    private static final String REPORT_SEARCH_HELP = "__report_search_help";\n    private static final String REPORT_RESOLVE = "__report_resolve";\n''', '''    private static final String REPORT_SEARCH_HELP = "__report_search_help";\n    private static final String REPORT_CATEGORY_FILTER = "__report_category_filter";\n    private static final String REPORT_SEARCH_FIELD_PREFIX = "__report_search_field:";\n    private static final String REPORT_FILTER_CATEGORY_PREFIX = "__report_filter_category:";\n    private static final String REPORT_NOTE_ADD = "__report_note_add";\n    private static final String REPORT_RESOLVE = "__report_resolve";\n''', 'Java report constants')

s = replace_once(s, '''            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);\n            case REPORT_SUBMIT_CATEGORY -> handleReportSubmitCategoryClick(player, holder, clicked);\n''', '''            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);\n            case REPORT_SEARCH_TYPE -> handleReportSearchTypeClick(player, holder, clicked);\n            case REPORT_SEARCH_INPUT -> handleReportSearchInputClick(player, holder, event.getSlot());\n            case REPORT_CATEGORY_FILTER -> handleReportCategoryFilterClick(player, holder, clicked);\n            case REPORT_CUSTOM_LIST -> handleReportCustomListClick(player, holder, clicked);\n            case REPORT_NOTE_INPUT -> handleReportNoteInputClick(player, holder, event.getSlot());\n            case REPORT_SUBMIT_CATEGORY -> handleReportSubmitCategoryClick(player, holder, clicked);\n''', 'Java report QoL click states')

# Expand the shared anvil prepare handler to Search + Note.
s = replace_once(s, '''        if (!(event.getInventory().getHolder() instanceof MenuHolder holder)) return;\n        if (holder.type() != MenuHolder.Type.REPORT_SUBMIT_REASON && holder.type() != MenuHolder.Type.REPORT_SUBMIT_EVIDENCE) return;\n''', '''        if (!(event.getInventory().getHolder() instanceof MenuHolder holder)) return;\n        if (holder.type() != MenuHolder.Type.REPORT_SUBMIT_REASON\n                && holder.type() != MenuHolder.Type.REPORT_SUBMIT_EVIDENCE\n                && holder.type() != MenuHolder.Type.REPORT_SEARCH_INPUT\n                && holder.type() != MenuHolder.Type.REPORT_NOTE_INPUT) return;\n''', 'Java anvil accepted holder types')
s = replace_once(s, '''        String fallback = holder.type() == MenuHolder.Type.REPORT_SUBMIT_REASON ? reportReasonPlaceholder() : reportEvidencePlaceholder();\n''', '''        String fallback = reportAnvilPlaceholder(holder.type());\n''', 'Java anvil placeholder resolver')

placeholder_marker = '''    private String reportReasonPlaceholder() {\n'''
placeholder_helpers = '''    private String reportAnvilPlaceholder(MenuHolder.Type type) {\n        return switch (type) {\n            case REPORT_SUBMIT_REASON -> reportReasonPlaceholder();\n            case REPORT_SUBMIT_EVIDENCE -> reportEvidencePlaceholder();\n            case REPORT_SEARCH_INPUT -> reportSearchPlaceholder();\n            case REPORT_NOTE_INPUT -> reportNotePlaceholder();\n            default -> "Ketik...";\n        };\n    }\n\n    private String reportSearchPlaceholder() {\n        String value = plugin.getConfig().getString("integrations.report.center.java-search-placeholder", "Ketik nama / UUID...");\n        return value == null || value.isBlank() ? "Ketik nama / UUID..." : value.trim();\n    }\n\n    private String reportNotePlaceholder() {\n        String value = plugin.getConfig().getString("integrations.report.center.java-note-placeholder", "Ketik catatan staff...");\n        return value == null || value.isBlank() ? "Ketik catatan staff..." : value.trim();\n    }\n\n'''
s = insert_before(s, placeholder_marker, placeholder_helpers, 'Java report QoL placeholders')

# Report Center buttons: direct Java search + category filtering.
s = replace_once(s, '''        if (plugin.getConfig().getBoolean("integrations.report.center.show-search", true)) {\n            inventory.setItem(22, navigationItem(Material.NAME_TAG, "&bCari Report", REPORT_SEARCH_HELP,\n                    "&7Gunakan command search:\\n&f/cdrmemberbook reports search <reporter|target|any> <nama>"));\n        }\n        inventory.setItem(31, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Member Menu."));\n''', '''        if (plugin.getConfig().getBoolean("integrations.report.center.show-search", true)) {\n            inventory.setItem(22, navigationItem(Material.NAME_TAG, "&bCari Report", REPORT_SEARCH_HELP,\n                    "&7Cari reporter / target langsung dari GUI."));\n        }\n        if (plugin.getConfig().getBoolean("integrations.report.center.show-category-filter", true)\n                && plugin.reports().categoriesEnabled()) {\n            inventory.setItem(24, navigationItem(Material.HOPPER, "&eFilter Kategori", REPORT_CATEGORY_FILTER,\n                    "&7Filter report berdasarkan kategori."));\n        }\n        inventory.setItem(31, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Member Menu."));\n''', 'Java Report Center search/category buttons')

old_recent = '''    private void showRecentReportList(Player player, String returnMenuId) {\n        if (!ensureReportStaff(player, returnMenuId)) return;\n        int limit = Math.max(1, Math.min(PAGE_SIZE, plugin.getConfig().getInt("integrations.report.recent-limit", 10)));\n        List<ReportService.ReportEntry> entries = plugin.reports().recent(limit, null);\n        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_LIST, null, returnMenuId, 0,\n                "ALL", 0, 54, "§8Reports §7• §eRecent");\n        Inventory inventory = holder.getInventory();\n        decorateFrame(inventory, player, 0, 1, "Recent Reports");\n        int slotIndex = 0;\n        for (ReportService.ReportEntry entry : entries) {\n            Material material = entry.status() == ReportService.Status.OPEN ? Material.WRITABLE_BOOK : Material.WRITTEN_BOOK;\n            ItemStack item = item(material, (entry.status() == ReportService.Status.OPEN ? "&c" : "&a") + "Report #" + entry.id() + " &8• &f" + entry.targetName(), List.of(\n                    "&7Reporter: &f" + entry.reporterName(), "&7Status: &f" + entry.status(), "&7Alasan: &f" + shorten(entry.reason(), 42), "", "&8» &fKlik untuk detail."));\n            ItemMeta meta = item.getItemMeta();\n            meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, REPORT_PREFIX + entry.id());\n            item.setItemMeta(meta);\n            inventory.setItem(CONTENT_SLOTS[slotIndex++], item);\n        }\n        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eReport Center", NAV_BACK, "&7Kembali ke Report Center."));\n        player.openInventory(inventory);\n    }\n'''
new_recent = '''    private void showRecentReportList(Player player, String returnMenuId) {\n        showReportCustomList(player, returnMenuId, "RECENT", 0);\n    }\n'''
s = replace_once(s, old_recent, new_recent, 'Java recent custom list')

s = replace_once(s, '''        else if (REPORT_SEARCH_HELP.equals(action)) {\n            player.closeInventory();\n            player.sendMessage(Colors.legacy("&bCari report: &f/cdrmemberbook reports search <reporter|target|any> <nama> [open|resolved|all]"));\n        }\n        else if (REPORT_REFRESH.equals(action)) showReportCenter(player, holder.menuId());\n''', '''        else if (REPORT_SEARCH_HELP.equals(action)) showReportSearchType(player, holder.menuId());\n        else if (REPORT_CATEGORY_FILTER.equals(action)) showReportCategoryFilter(player, holder.menuId());\n        else if (REPORT_REFRESH.equals(action)) showReportCenter(player, holder.menuId());\n''', 'Java center direct search/category handlers')

# Insert full Java Search / Category / Custom list QoL before regular status list.
marker = '''    private void showReportList(Player player, String returnMenuId, ReportService.Status filter, int requestedPage) {\n'''
qol_methods = r'''    private void showReportSearchType(Player player, String returnMenuId) {
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

'''
s = insert_before(s, marker, qol_methods, 'Java Report Center QoL methods')

# Make detail navigation preserve custom search/category/recent context.
s = replace_once(s, '''    private void showReportDetail(Player player, String returnMenuId, ReportService.Status filter, int page, int reportId) {\n        if (!ensureReportStaff(player, returnMenuId)) return;\n''', '''    private void showReportDetail(Player player, String returnMenuId, ReportService.Status filter, int page, int reportId) {\n        showReportDetail(player, returnMenuId, statusContext(filter), page, reportId);\n    }\n\n    private void showReportDetail(Player player, String returnMenuId, String listContext, int page, int reportId) {\n        if (!ensureReportStaff(player, returnMenuId)) return;\n''', 'Java report detail overload')
s = replace_once(s, '''            showReportList(player, returnMenuId, filter, page);\n            return;\n        }\n        String filterName = filter == null ? "ALL" : filter.name();\n        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_DETAIL, null, returnMenuId, page,\n                filterName, reportId, 27, trimTitle("§8Report §7• §f#" + reportId));\n''', '''            showReportListContext(player, returnMenuId, listContext, page);\n            return;\n        }\n        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_DETAIL, null, returnMenuId, page,\n                listContext, reportId, 27, trimTitle("§8Report §7• §f#" + reportId));\n''', 'Java report detail list context')

s = replace_once(s, '''        inventory.setItem(22, item(Material.PAPER, "&eStaff Note / Audit", List.of(\n                "&7Tambah note lewat command:",\n                "&f/cdrmemberbook report note " + reportId + " <catatan>",\n                "",\n                "&7Lihat audit:",\n                "&f/cdrmemberbook report audit " + reportId\n        )));\n''', '''        inventory.setItem(22, navigationItem(Material.PAPER, "&eTambah Staff Note", REPORT_NOTE_ADD,\n                "&7Klik untuk menambah catatan staff via Anvil UI.\\n&8Audit tetap tersimpan otomatis."));\n''', 'Java detail native note button')

s = replace_once(s, '''        ReportService.Status filter = parseFilter(holder.context());\n        if (NAV_BACK.equals(action)) { showReportList(player, holder.menuId(), filter, holder.page()); return; }\n        if (REPORT_RESOLVE.equals(action)) showReportConfirm(player, holder.menuId(), filter, holder.page(), holder.value(), "resolve");\n        else if (REPORT_REOPEN.equals(action)) showReportConfirm(player, holder.menuId(), filter, holder.page(), holder.value(), "reopen");\n        else if (REPORT_DELETE.equals(action)) showReportConfirm(player, holder.menuId(), filter, holder.page(), holder.value(), "delete");\n''', '''        String listContext = holder.context();\n        if (NAV_BACK.equals(action)) { showReportListContext(player, holder.menuId(), listContext, holder.page()); return; }\n        if (REPORT_RESOLVE.equals(action)) showReportConfirm(player, holder.menuId(), listContext, holder.page(), holder.value(), "resolve");\n        else if (REPORT_REOPEN.equals(action)) showReportConfirm(player, holder.menuId(), listContext, holder.page(), holder.value(), "reopen");\n        else if (REPORT_DELETE.equals(action)) showReportConfirm(player, holder.menuId(), listContext, holder.page(), holder.value(), "delete");\n        else if (REPORT_NOTE_ADD.equals(action)) showReportNoteInput(player, holder.menuId(), listContext, holder.page(), holder.value());\n''', 'Java detail list context/native note handler')

# Add Staff Note Anvil methods before confirmation method.
confirm_marker = '''    private void showReportConfirm(Player player, String returnMenuId, ReportService.Status filter, int page,\n'''
# The signature was still old at this point; insert then replace signature below.
note_methods = r'''    private void showReportNoteInput(Player player, String returnMenuId, String listContext, int page, int reportId) {
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

'''
s = insert_before(s, confirm_marker, note_methods, 'Java native staff-note methods')

# Confirmation methods now keep generic list context instead of status-only context.
s = replace_once(s, '''    private void showReportConfirm(Player player, String returnMenuId, ReportService.Status filter, int page,\n                                   int reportId, String operation) {\n''', '''    private void showReportConfirm(Player player, String returnMenuId, String listContext, int page,\n                                   int reportId, String operation) {\n''', 'Java report confirm context signature')
s = replace_once(s, '''            showReportList(player, returnMenuId, filter, page);\n            return;\n        }\n        String filterName = filter == null ? "ALL" : filter.name();\n        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CONFIRM, null, returnMenuId, page,\n                operation + "|" + filterName, reportId, 27, "§8Konfirmasi Report");\n''', '''            showReportListContext(player, returnMenuId, listContext, page);\n            return;\n        }\n        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_CONFIRM, null, returnMenuId, page,\n                operation + "\\n" + listContext, reportId, 27, "§8Konfirmasi Report");\n''', 'Java report confirm holder context')
s = replace_once(s, '''        String[] parts = holder.context().split("\\\\|", 2);\n        String operation = parts.length > 0 ? parts[0] : "";\n        ReportService.Status filter = parts.length > 1 ? parseFilter(parts[1]) : null;\n        if (REPORT_CANCEL.equals(action)) {\n            showReportDetail(player, holder.menuId(), filter, holder.page(), holder.value());\n''', '''        String[] parts = holder.context().split("\\\\n", 2);\n        String operation = parts.length > 0 ? parts[0] : "";\n        String listContext = parts.length > 1 ? parts[1] : statusContext(null);\n        if (REPORT_CANCEL.equals(action)) {\n            showReportDetail(player, holder.menuId(), listContext, holder.page(), holder.value());\n''', 'Java report confirm parse list context')
s = replace_once(s, '''            showReportList(player, holder.menuId(), filter, holder.page());\n            return;\n''', '''            showReportListContext(player, holder.menuId(), listContext, holder.page());\n            return;\n''', 'Java report confirm failure return')
s = replace_once(s, '''        if (operation.equals("delete")) showReportList(player, holder.menuId(), filter, holder.page());\n        else showReportDetail(player, holder.menuId(), filter, holder.page(), holder.value());\n''', '''        if (operation.equals("delete")) showReportListContext(player, holder.menuId(), listContext, holder.page());\n        else showReportDetail(player, holder.menuId(), listContext, holder.page(), holder.value());\n''', 'Java report confirm success return')

# Add category to ordinary list rows as well.
s = replace_once(s, '''                    "&7Reporter: &f" + entry.reporterName(),\n                    "&7Target: &f" + entry.targetName(),\n                    "&7Status: &f" + entry.status(),\n''', '''                    "&7Reporter: &f" + entry.reporterName(),\n                    "&7Target: &f" + entry.targetName(),\n                    "&7Kategori: &f" + plugin.reports().categoryLabel(entry.category()),\n                    "&7Status: &f" + entry.status(),\n''', 'Java report list category lore')

write(p, s)

# ---- Admin health/version ----
p = 'src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'
s = read(p)
s = s.replace('v1.9.7', 'v1.9.8')
write(p, s)

# ---- README ----
p = 'README.md'
s = read(p)
s = replace_once(s, '# CdrMemberBook v1.9.7', '# CdrMemberBook v1.9.8', 'README version')
s = replace_once(s, '''Bedrock additionally has native search input and native staff-note input through Forms. Java search, note, and full audit lookup are also available through admin commands.\n''', '''Bedrock has native search and staff-note Forms. Java staff now also has native Anvil search, category filters, paginated search/category results, and native staff-note input directly from Report Center. Admin commands remain available as a fallback.\n''', 'README Report Center parity')
write(p, s)

# ---- Changelog ----
p = 'CHANGELOG.md'
s = read(p)
entry = '''## 1.9.8 - Report Center Java QoL\n\n- Added native Java Report Center search selector for reporter, target, or ANY lookup.\n- Added Anvil-based Java search input without requiring admin commands or chat interception.\n- Added native Java category filter with per-category report counts.\n- Added paginated Java custom result lists for Recent, Search, and Category views.\n- Preserved Search/Category/Recent context when opening report details, resolving/reopening/deleting, or returning to results.\n- Added native Java Staff Note input via Anvil with max-length validation and audit persistence.\n- Added category labels to Java report list rows and kept all report permission checks on every callback.\n- Config migrated to version 25 with Java Report Center search/note UI settings.\n\n'''
s = replace_once(s, '# Changelog\n\n', '# Changelog\n\n' + entry, 'CHANGELOG v1.9.8')
write(p, s)
