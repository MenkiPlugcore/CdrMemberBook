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

# Versions
p = 'pom.xml'
s = read(p)
s = replace_once(s, '<version>1.9.5</version>', '<version>1.9.6</version>', 'pom version')
write(p, s)

p = 'src/main/resources/plugin.yml'
s = read(p)
s = replace_once(s, "version: '1.9.5'", "version: '1.9.6'", 'plugin version')
write(p, s)

# MenuHolder: support Java native anvil input and submit flow holder types.
p = 'src/main/java/id/cadera/memberbook/gui/MenuHolder.java'
s = read(p)
s = replace_once(s, 'import org.bukkit.inventory.InventoryHolder;\n', 'import org.bukkit.inventory.InventoryHolder;\nimport org.bukkit.event.inventory.InventoryType;\n', 'MenuHolder InventoryType import')
s = replace_once(s, '''        REPORT_DETAIL,\n        REPORT_CONFIRM\n''', '''        REPORT_DETAIL,\n        REPORT_CONFIRM,\n        REPORT_SUBMIT_PLAYER,\n        REPORT_SUBMIT_REASON,\n        REPORT_SUBMIT_CONFIRM\n''', 'MenuHolder report submit types')
constructor_marker = '''    public MenuHolder(Type type, UUID targetId, String menuId, int page,\n                      String context, int value, int size, String title) {\n'''
anvil_constructor = '''    public MenuHolder(Type type, UUID targetId, String menuId, int page,\n                      InventoryType inventoryType, String title) {\n        this.type = type;\n        this.targetId = targetId;\n        this.menuId = menuId == null ? "main" : menuId;\n        this.page = Math.max(0, page);\n        this.context = "";\n        this.value = 0;\n        this.inventory = Bukkit.createInventory(this, inventoryType, title);\n    }\n\n'''
s = insert_before(s, constructor_marker, anvil_constructor, 'MenuHolder anvil constructor')
write(p, s)

# MenuConfigService: Java report button is native when built-in report is enabled.
p = 'src/main/java/id/cadera/memberbook/menu/MenuConfigService.java'
s = read(p)
old = '''            case "report" -> (plugin.reports()!=null && plugin.reports().enabled() && plugin.forms()!=null && plugin.forms().isBedrock(player)) ? new Availability(true,"ok","native-report") : availableCommand(button.command());\n'''
new = '''            case "report" -> {\n                boolean nativeReport = plugin.reports()!=null && plugin.reports().enabled();\n                boolean bedrock = plugin.forms()!=null && plugin.forms().isBedrock(player);\n                boolean javaSubmit = plugin.getConfig().getBoolean("integrations.report.java-submit.enabled", true);\n                if (nativeReport && (bedrock || javaSubmit))\n                    yield new Availability(true,"ok", bedrock ? "native-report-bedrock" : "native-report-java");\n                yield availableCommand(button.command());\n            }\n'''
s = replace_once(s, old, new, 'MenuConfig native Java report availability')
write(p, s)

# JavaMenuService native report submit flow.
p = 'src/main/java/id/cadera/memberbook/gui/JavaMenuService.java'
s = read(p)
s = replace_once(s, 'import org.bukkit.event.inventory.InventoryClickEvent;\n', 'import org.bukkit.event.inventory.InventoryClickEvent;\nimport org.bukkit.event.inventory.InventoryType;\nimport org.bukkit.event.inventory.PrepareAnvilEvent;\n', 'JavaMenu event imports')
s = replace_once(s, 'import org.bukkit.inventory.Inventory;\n', 'import org.bukkit.inventory.AnvilInventory;\nimport org.bukkit.inventory.Inventory;\n', 'JavaMenu AnvilInventory import')
s = replace_once(s, '''    private static final String REPORT_CANCEL = "__report_cancel";\n''', '''    private static final String REPORT_CANCEL = "__report_cancel";\n    private static final String REPORT_SUBMIT_SEND = "__report_submit_send";\n    private static final String REPORT_SUBMIT_EDIT = "__report_submit_edit";\n    private static final String REPORT_SUBMIT_CANCEL = "__report_submit_cancel";\n''', 'JavaMenu submit constants')
s = replace_once(s, '''            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);\n''', '''            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);\n            case REPORT_SUBMIT_PLAYER -> handleReportSubmitPlayerClick(player, holder, clicked);\n            case REPORT_SUBMIT_REASON -> handleReportReasonClick(player, holder, event.getSlot());\n            case REPORT_SUBMIT_CONFIRM -> handlePlayerReportConfirmClick(player, holder, clicked);\n''', 'JavaMenu click switch')
s = replace_once(s, '''            case "homes", "pay", "trade", "report" -> { player.closeInventory(); plugin.executeMenuCommand(player, button); }\n            case "teleport" -> showPlayerSelect(player, menu.id(), 0);\n''', '''            case "homes", "pay", "trade" -> { player.closeInventory(); plugin.executeMenuCommand(player, button); }\n            case "report" -> {\n                if (plugin.reports() != null && plugin.reports().enabled()\n                        && plugin.getConfig().getBoolean("integrations.report.java-submit.enabled", true)) {\n                    showReportSubmitPlayerSelect(player, menu.id(), 0);\n                } else {\n                    player.closeInventory();\n                    plugin.executeMenuCommand(player, button);\n                }\n            }\n            case "teleport" -> showPlayerSelect(player, menu.id(), 0);\n''', 'JavaMenu configured report click')

submit_methods = r'''    // ---- Java Native Report Submit ----

    private void showReportSubmitPlayerSelect(Player player, String returnMenuId, int requestedPage) {
        if (plugin.reports() == null || !plugin.reports().enabled()) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, returnMenuId, 0);
            return;
        }
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
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_PLAYER, null, returnMenuId, page, 54,
                "§8Lapor Player §7• §fPilih Target");
        Inventory inventory = holder.getInventory();
        decorateFrame(inventory, player, page, totalPages, "Lapor Player");

        int slotIndex = 0;
        for (int i = start; i < end; i++) {
            Player target = players.get(i);
            ItemStack head = new ItemStack(Material.PLAYER_HEAD);
            SkullMeta meta = (SkullMeta) head.getItemMeta();
            meta.setDisplayName(Colors.legacy("&c&l" + target.getName()));
            meta.setLore(List.of(
                    Colors.legacy("&7World: &f" + target.getWorld().getName()),
                    Colors.legacy(""),
                    Colors.legacy("&8» &fKlik untuk melaporkan player ini.")
            ));
            meta.setOwningPlayer(target);
            meta.getPersistentDataContainer().set(plugin.playerKey(), PersistentDataType.STRING, target.getUniqueId().toString());
            head.setItemMeta(meta);
            inventory.setItem(CONTENT_SLOTS[slotIndex++], head);
        }
        if (page > 0) inventory.setItem(45, navigationItem(Material.ARROW, "&eHalaman Sebelumnya", NAV_PREVIOUS, "&7Lihat player sebelumnya."));
        inventory.setItem(49, navigationItem(Material.OAK_DOOR, "&eKembali", NAV_BACK, "&7Kembali ke Member Menu."));
        if (page < totalPages - 1) inventory.setItem(53, navigationItem(Material.ARROW, "&eHalaman Berikutnya", NAV_NEXT, "&7Lihat player berikutnya."));
        player.openInventory(inventory);
    }

    private void handleReportSubmitPlayerClick(Player player, MenuHolder holder, ItemStack clicked) {
        String nav = action(clicked);
        if (NAV_PREVIOUS.equals(nav)) { showReportSubmitPlayerSelect(player, holder.menuId(), holder.page() - 1); return; }
        if (NAV_NEXT.equals(nav)) { showReportSubmitPlayerSelect(player, holder.menuId(), holder.page() + 1); return; }
        if (NAV_BACK.equals(nav)) { showConfiguredMenu(player, holder.menuId(), 0); return; }
        if (!clicked.hasItemMeta()) return;
        String raw = clicked.getItemMeta().getPersistentDataContainer().get(plugin.playerKey(), PersistentDataType.STRING);
        if (raw == null) return;
        try {
            Player target = Bukkit.getPlayer(UUID.fromString(raw));
            if (target == null) {
                plugin.message(player, "player-not-found");
                showReportSubmitPlayerSelect(player, holder.menuId(), holder.page());
                return;
            }
            showReportReasonInput(player, target, holder.menuId());
        } catch (IllegalArgumentException ignored) { }
    }

    private void showReportReasonInput(Player player, Player target, String returnMenuId) {
        if (target == null || !target.isOnline()) {
            plugin.message(player, "player-not-found");
            showReportSubmitPlayerSelect(player, returnMenuId, 0);
            return;
        }
        String rawTitle = plugin.getConfig().getString("integrations.report.java-submit.reason-title", "&8Lapor • Alasan");
        String title = trimTitle(Colors.legacy(rawTitle == null ? "&8Lapor • Alasan" : rawTitle));
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_REASON, target.getUniqueId(), returnMenuId, 0,
                InventoryType.ANVIL, title);
        AnvilInventory inventory = (AnvilInventory) holder.getInventory();
        String placeholder = reportReasonPlaceholder();
        Material material = material(plugin.getConfig().getString("integrations.report.java-submit.reason-material", "PAPER"), Material.PAPER);
        ItemStack input = item(material, "&f" + placeholder, List.of(
                "&7Target: &f" + target.getName(),
                "&7Ketik alasan laporan di kolom nama.",
                "&7Lalu klik hasil di slot kanan.",
                "",
                "&8ESC untuk membatalkan."
        ));
        inventory.setItem(0, input);
        inventory.setRepairCost(0);
        player.openInventory(inventory);
    }

    @EventHandler
    public void onPrepareReportAnvil(PrepareAnvilEvent event) {
        if (!(event.getInventory().getHolder() instanceof MenuHolder holder)
                || holder.type() != MenuHolder.Type.REPORT_SUBMIT_REASON) return;
        AnvilInventory inventory = event.getInventory();
        inventory.setRepairCost(0);
        String reason = inventory.getRenameText();
        ItemStack input = inventory.getItem(0);
        if (input == null || input.getType().isAir()) return;
        ItemStack result = input.clone();
        ItemMeta meta = result.getItemMeta();
        String display = reason == null || reason.isBlank() ? reportReasonPlaceholder() : reason.trim();
        meta.setDisplayName(Colors.legacy("&f" + shorten(display, 48)));
        result.setItemMeta(meta);
        event.setResult(result);
    }

    private void handleReportReasonClick(Player player, MenuHolder holder, int slot) {
        if (slot != 2 || !(holder.getInventory() instanceof AnvilInventory inventory)) return;
        if (holder.targetId() == null) return;
        Player target = Bukkit.getPlayer(holder.targetId());
        if (target == null) {
            plugin.message(player, "player-not-found");
            showReportSubmitPlayerSelect(player, holder.menuId(), 0);
            return;
        }
        String reason = inventory.getRenameText();
        if (reason == null) reason = "";
        reason = reason.trim();
        if (reason.equalsIgnoreCase(reportReasonPlaceholder())) reason = "";
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) {
            plugin.message(player, "report-reason-too-short", "%min%", Integer.toString(min));
            Bukkit.getScheduler().runTask(plugin, () -> {
                Player current = Bukkit.getPlayer(target.getUniqueId());
                if (player.isOnline() && current != null) showReportReasonInput(player, current, holder.menuId());
            });
            return;
        }
        if (reason.length() > max) {
            plugin.message(player, "report-reason-too-long", "%max%", Integer.toString(max));
            Bukkit.getScheduler().runTask(plugin, () -> {
                Player current = Bukkit.getPlayer(target.getUniqueId());
                if (player.isOnline() && current != null) showReportReasonInput(player, current, holder.menuId());
            });
            return;
        }
        showPlayerReportConfirm(player, target, reason, holder.menuId());
    }

    private void showPlayerReportConfirm(Player player, Player target, String reason, String returnMenuId) {
        if (target == null || !target.isOnline()) {
            plugin.message(player, "player-not-found");
            showReportSubmitPlayerSelect(player, returnMenuId, 0);
            return;
        }
        MenuHolder holder = new MenuHolder(MenuHolder.Type.REPORT_SUBMIT_CONFIRM, target.getUniqueId(), returnMenuId, 0,
                reason, 0, 27, trimTitle("§8Konfirmasi §7• §c" + target.getName()));
        Inventory inventory = holder.getInventory();
        fillAll(inventory, filler(Material.BLACK_STAINED_GLASS_PANE));

        ItemStack head = new ItemStack(Material.PLAYER_HEAD);
        SkullMeta headMeta = (SkullMeta) head.getItemMeta();
        headMeta.setOwningPlayer(target);
        headMeta.setDisplayName(Colors.legacy("&c&lLaporkan " + target.getName()));
        List<String> lore = new ArrayList<>();
        lore.add(Colors.legacy("&7Alasan:"));
        for (String line : wrapText(reason, 36)) lore.add(Colors.legacy("&f" + line));
        headMeta.setLore(lore);
        head.setItemMeta(headMeta);
        inventory.setItem(13, head);
        inventory.setItem(10, navigationItem(Material.LIME_CONCRETE, "&a&lKIRIM LAPORAN", REPORT_SUBMIT_SEND,
                "&7Kirim report ini ke staff."));
        inventory.setItem(16, navigationItem(Material.ANVIL, "&eEdit Alasan", REPORT_SUBMIT_EDIT,
                "&7Kembali ke input alasan."));
        inventory.setItem(22, navigationItem(Material.BARRIER, "&cBatal", REPORT_SUBMIT_CANCEL,
                "&7Batalkan report dan kembali ke menu."));
        player.openInventory(inventory);
    }

    private void handlePlayerReportConfirmClick(Player player, MenuHolder holder, ItemStack clicked) {
        String action = action(clicked);
        if (action == null || holder.targetId() == null) return;
        Player target = Bukkit.getPlayer(holder.targetId());
        if (REPORT_SUBMIT_CANCEL.equals(action)) {
            showConfiguredMenu(player, holder.menuId(), 0);
            return;
        }
        if (target == null) {
            plugin.message(player, "player-not-found");
            showReportSubmitPlayerSelect(player, holder.menuId(), 0);
            return;
        }
        if (REPORT_SUBMIT_EDIT.equals(action)) {
            showReportReasonInput(player, target, holder.menuId());
            return;
        }
        if (!REPORT_SUBMIT_SEND.equals(action)) return;
        ReportService.SubmitResult result = plugin.reports().submit(player, target, holder.context());
        if (result.success()) {
            plugin.message(player, "report-sent", "%id%", Integer.toString(result.id()), "%player%", target.getName());
            showConfiguredMenu(player, holder.menuId(), 0);
        } else if ("cooldown".equals(result.reasonCode())) {
            plugin.message(player, "report-cooldown", "%seconds%", Long.toString(result.waitSeconds()));
            showConfiguredMenu(player, holder.menuId(), 0);
        } else if ("duplicate".equals(result.reasonCode())) {
            plugin.message(player, "report-duplicate", "%id%", Integer.toString(result.id()),
                    "%seconds%", Long.toString(result.waitSeconds()));
            showConfiguredMenu(player, holder.menuId(), 0);
        } else if ("self".equals(result.reasonCode())) {
            plugin.message(player, "cannot-report-self");
            showReportSubmitPlayerSelect(player, holder.menuId(), 0);
        } else if ("short".equals(result.reasonCode())) {
            int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
            plugin.message(player, "report-reason-too-short", "%min%", Integer.toString(min));
            showReportReasonInput(player, target, holder.menuId());
        } else {
            plugin.message(player, "report-failed");
            showConfiguredMenu(player, holder.menuId(), 0);
        }
    }

    private String reportReasonPlaceholder() {
        String value = plugin.getConfig().getString("integrations.report.java-submit.reason-placeholder", "Ketik alasan laporan...");
        return value == null || value.isBlank() ? "Ketik alasan laporan..." : value.trim();
    }

    private List<String> wrapText(String value, int width) {
        if (value == null || value.isBlank()) return List.of("");
        int safeWidth = Math.max(12, width);
        List<String> lines = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (String word : value.trim().split("\\s+")) {
            if (current.length() > 0 && current.length() + 1 + word.length() > safeWidth) {
                lines.add(current.toString());
                current.setLength(0);
            }
            if (current.length() > 0) current.append(' ');
            current.append(word);
        }
        if (current.length() > 0) lines.add(current.toString());
        return lines.isEmpty() ? List.of(value) : List.copyOf(lines);
    }

'''
s = insert_before(s, '    // ---- Java Staff Report Center ----\n', submit_methods, 'Java native report methods')
write(p, s)

# Main plugin migration/version.
p = 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = read(p)
s = s.replace('CdrMemberBook v1.9.5 enabled.', 'CdrMemberBook v1.9.6 enabled.')
old = '''        if (configVersion < 22) {\n            getConfig().set("integrations.report.duplicate-window-seconds", 300L);\n            getConfig().set("integrations.report.recent-limit", 10);\n            getConfig().set("integrations.report.audit.max-history", 50);\n            getConfig().set("integrations.report.audit.max-notes", 20);\n            getConfig().set("integrations.report.audit.max-note-length", 240);\n            getConfig().set("integrations.report.center.show-recent", true);\n            getConfig().set("integrations.report.center.show-search", true);\n            getConfig().set("integrations.report.center.detail-note-limit", 3);\n            getConfig().set("integrations.report.center.detail-audit-limit", 5);\n        }\n\n        getConfig().set("config-version", 22);\n'''
new = '''        if (configVersion < 22) {\n            getConfig().set("integrations.report.duplicate-window-seconds", 300L);\n            getConfig().set("integrations.report.recent-limit", 10);\n            getConfig().set("integrations.report.audit.max-history", 50);\n            getConfig().set("integrations.report.audit.max-notes", 20);\n            getConfig().set("integrations.report.audit.max-note-length", 240);\n            getConfig().set("integrations.report.center.show-recent", true);\n            getConfig().set("integrations.report.center.show-search", true);\n            getConfig().set("integrations.report.center.detail-note-limit", 3);\n            getConfig().set("integrations.report.center.detail-audit-limit", 5);\n        }\n\n        if (configVersion < 23) {\n            getConfig().set("integrations.report.java-submit.enabled", true);\n            getConfig().set("integrations.report.java-submit.reason-title", "&8Lapor • Alasan");\n            getConfig().set("integrations.report.java-submit.reason-placeholder", "Ketik alasan laporan...");\n            getConfig().set("integrations.report.java-submit.reason-material", "PAPER");\n        }\n\n        getConfig().set("config-version", 23);\n'''
s = replace_once(s, old, new, 'config migration v23')
write(p, s)

# Admin version labels.
p = 'src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'
s = read(p)
s = s.replace('&fv1.9.5', '&fv1.9.6')
write(p, s)

# Config v23.
p = 'src/main/resources/config.yml'
s = read(p)
s = replace_once(s, '# CdrMemberBook v1.9.5\nconfig-version: 22', '# CdrMemberBook v1.9.6\nconfig-version: 23', 'config header')
center_marker = '''    # Native Java + Bedrock staff Report Center. Java staff UI akan ditambahkan terpisah.\n    center:\n'''
java_submit_cfg = '''    # Native Java player report submit. Tidak membutuhkan plugin /report eksternal.\n    java-submit:\n      enabled: true\n      # Input alasan memakai UI Anvil native Java agar tidak menyadap chat player.\n      reason-title: '&8Lapor • Alasan'\n      reason-placeholder: 'Ketik alasan laporan...'\n      reason-material: PAPER\n\n    # Native Java + Bedrock staff Report Center.\n    center:\n'''
s = replace_once(s, center_marker, java_submit_cfg, 'java submit config')
s = replace_once(s, "  report-reason-too-short: '&eAlasan laporan minimal &f%min% &ekarakter.'\n", "  report-reason-too-short: '&eAlasan laporan minimal &f%min% &ekarakter.'\n  report-reason-too-long: '&eAlasan laporan maksimal &f%max% &ekarakter.'\n", 'too long message')
s = s.replace('# Java fallback jika ada plugin eksternal dengan /report. Bedrock memakai report native CdrMemberBook.', '# Java dan Bedrock memakai native report CdrMemberBook. `command` hanya fallback jika native report dimatikan.')
write(p, s)

# README + changelog.
p = 'README.md'
s = read(p)
s = s.replace('# CdrMemberBook v1.9.5', '# CdrMemberBook v1.9.6', 1)
s = s.replace('target/CdrMemberBook-1.9.5.jar', 'target/CdrMemberBook-1.9.6.jar')
section = '''\n## Java Native Report Submit v1.9.6\n\nPlayer Java sekarang memakai flow report bawaan yang sama dengan Bedrock dan tidak membutuhkan plugin `/report` eksternal. Klik tombol **Lapor** → pilih player online → ketik alasan pada UI Anvil native → cek halaman konfirmasi → kirim. Submit tetap memakai `ReportService`, sehingga cooldown, anti-duplicate v1.9.5, persistence `reports.yml`, staff notification, console hook, dan audit tetap konsisten lintas Java/Bedrock.\n\n```yaml\nintegrations:\n  report:\n    java-submit:\n      enabled: true\n      reason-title: '&8Lapor • Alasan'\n      reason-placeholder: 'Ketik alasan laporan...'\n      reason-material: PAPER\n```\n\nMenutup Anvil dengan ESC membatalkan input tanpa menyimpan report. Target yang logout di tengah flow akan ditolak aman dan player dikembalikan ke picker.\n'''
if '## Java Native Report Submit v1.9.6' not in s:
    s += section
write(p, s)

p = 'CHANGELOG.md'
s = read(p)
entry = '''# Changelog\n\n## 1.9.6 - Java Native Report Submit\n\n- Added fully native Java report submission without requiring an external `/report` plugin.\n- Added Java inventory target picker with pagination and self-target exclusion.\n- Added native Anvil reason input, configurable title/placeholder/material, min/max validation and no chat interception.\n- Added Java confirmation GUI with target head, wrapped reason preview, Edit, Cancel and Send actions.\n- Java and Bedrock submissions now share the same `ReportService`, cooldown, anti-duplicate protection, persistence, staff notifications and audit pipeline.\n- Added config migration v23 and Java-native report availability detection.\n\n'''
s = replace_once(s, '# Changelog\n\n', entry, 'changelog v1.9.6')
write(p, s)

print('v1.9.6 patch applied')
