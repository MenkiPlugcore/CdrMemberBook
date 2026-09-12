from pathlib import Path

root = Path('.')

def read(path): return (root / path).read_text()
def write(path, content): (root / path).write_text(content)
def replace_once(text, old, new, label):
    if old not in text: raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)
def replace_between(text, start, end, block, label):
    a = text.find(start)
    if a < 0: raise SystemExit(f'start marker not found: {label}')
    b = text.find(end, a)
    if b < 0: raise SystemExit(f'end marker not found: {label}')
    return text[:a] + block + text[b:]

# Versions
p='pom.xml'; s=read(p); s=replace_once(s,'<version>1.9.6</version>','<version>1.9.7</version>','pom'); write(p,s)
p='src/main/resources/plugin.yml'; s=read(p); s=replace_once(s,"version: '1.9.6'","version: '1.9.7'",'plugin'); write(p,s)

# ReportService: categories + evidence + backwards-compatible storage.
p='src/main/java/id/cadera/memberbook/report/ReportService.java'; s=read(p)
start='    public SubmitResult submit(Player reporter, Player target, String rawReason) {'
end='    public ReportEntry get(int id) {'
submit_block=r'''    public SubmitResult submit(Player reporter, Player target, String rawReason) {
        return submit(reporter, target, "OTHER", rawReason, "");
    }

    public SubmitResult submit(Player reporter, Player target, String rawCategory, String rawReason, String rawEvidence) {
        if (!enabled()) return new SubmitResult(false, 0, 0, "disabled");
        if (reporter.getUniqueId().equals(target.getUniqueId())) return new SubmitResult(false, 0, 0, "self");

        String category = categoriesEnabled() ? normalizeCategory(rawCategory) : "OTHER";
        if (categoriesEnabled() && !categories().contains(category)) return new SubmitResult(false, 0, 0, "category");
        String reason = sanitizeText(rawReason);
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) return new SubmitResult(false, 0, 0, "short");
        if (reason.length() > max) reason = reason.substring(0, max).trim();

        String evidence = plugin.getConfig().getBoolean("integrations.report.evidence.enabled", true)
                ? sanitizeText(rawEvidence) : "";
        String evidenceValidation = validateEvidence(evidence);
        if (!"ok".equals(evidenceValidation)) return new SubmitResult(false, 0, 0, evidenceValidation);

        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(reporter.getUniqueId(), 0L);
        if (until > now) return new SubmitResult(false, 0, Math.max(1L, (until - now + 999L) / 1000L), "cooldown");

        DuplicateMatch duplicate = findDuplicate(reporter.getUniqueId(), target.getUniqueId(), now);
        if (duplicate != null) return new SubmitResult(false, duplicate.id(), duplicate.waitSeconds(), "duplicate");

        int id = Math.max(1, data.getInt("next-id", 1));
        String base = "reports." + id + ".";
        String createdAt = Instant.now().toString();
        data.set(base + "status", Status.OPEN.name());
        data.set(base + "created-at", createdAt);
        data.set(base + "reporter.name", reporter.getName());
        data.set(base + "reporter.uuid", reporter.getUniqueId().toString());
        data.set(base + "target.name", target.getName());
        data.set(base + "target.uuid", target.getUniqueId().toString());
        data.set(base + "category", category);
        data.set(base + "reason", reason);
        data.set(base + "evidence", evidence);
        data.set(base + "world", reporter.getWorld().getName());
        data.set(base + "location.x", reporter.getLocation().getBlockX());
        data.set(base + "location.y", reporter.getLocation().getBlockY());
        data.set(base + "location.z", reporter.getLocation().getBlockZ());
        data.set(base + "resolved-at", null);
        data.set(base + "resolved-by", null);
        data.set(base + "notes", new ArrayList<>());
        data.set(base + "audit", new ArrayList<>());
        appendAuditInMemory(id, "CREATE", reporter.getName(), "[" + category + "] Report dibuat untuk " + target.getName());
        data.set("next-id", id + 1);
        if (!save()) {
            reloadFromDisk();
            return new SubmitResult(false, 0, 0, "storage");
        }

        long cooldown = Math.max(0L, plugin.getConfig().getLong("integrations.report.cooldown-seconds", 60L));
        if (cooldown > 0L) cooldownUntil.put(reporter.getUniqueId(), now + cooldown * 1000L);
        notifyStaff(id, reporter, target, category, reason, evidence);
        runConsoleHook(id, reporter, target, category, reason, evidence);
        plugin.getLogger().info("Report #" + id + " [" + category + "]: " + reporter.getName() + " -> " + target.getName() + " | " + reason);
        return new SubmitResult(true, id, 0, "ok");
    }

    public boolean categoriesEnabled() {
        return plugin.getConfig().getBoolean("integrations.report.categories.enabled", true);
    }

    public List<String> categories() {
        List<String> configured = plugin.getConfig().getStringList("integrations.report.categories.values");
        if (configured.isEmpty()) configured = List.of("CHEATING", "GRIEFING", "TOXIC", "SCAM", "BUG_ABUSE", "OTHER");
        List<String> out = new ArrayList<>();
        for (String raw : configured) {
            String normalized = normalizeCategory(raw);
            if (!normalized.isBlank() && !out.contains(normalized)) out.add(normalized);
        }
        if (out.isEmpty()) out.add("OTHER");
        return List.copyOf(out);
    }

    public String normalizeCategory(String raw) {
        String value = raw == null ? "" : raw.trim().toUpperCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        value = value.replaceAll("[^A-Z0-9_]", "");
        return value.isBlank() ? "OTHER" : value;
    }

    public String categoryLabel(String raw) {
        String category = normalizeCategory(raw);
        String configured = plugin.getConfig().getString("integrations.report.categories.labels." + category);
        if (configured != null && !configured.isBlank()) return configured;
        String[] parts = category.toLowerCase(Locale.ROOT).split("_");
        StringBuilder out = new StringBuilder();
        for (String part : parts) {
            if (part.isBlank()) continue;
            if (out.length() > 0) out.append(' ');
            out.append(Character.toUpperCase(part.charAt(0))).append(part.substring(1));
        }
        return out.length() == 0 ? "Other" : out.toString();
    }

    public String validateEvidence(String rawEvidence) {
        if (!plugin.getConfig().getBoolean("integrations.report.evidence.enabled", true)) return "ok";
        String evidence = sanitizeText(rawEvidence);
        boolean optional = plugin.getConfig().getBoolean("integrations.report.evidence.optional", true);
        if (evidence.isBlank()) return optional ? "ok" : "evidence-required";
        int max = Math.max(20, plugin.getConfig().getInt("integrations.report.evidence.max-length", 300));
        if (evidence.length() > max) return "evidence-too-long";
        if (plugin.getConfig().getBoolean("integrations.report.evidence.require-http-url-if-link", true)
                && evidence.matches("(?i)^[a-z][a-z0-9+.-]*://.*")
                && !(evidence.toLowerCase(Locale.ROOT).startsWith("http://") || evidence.toLowerCase(Locale.ROOT).startsWith("https://"))) {
            return "evidence-invalid-link";
        }
        return "ok";
    }

'''
s=replace_between(s,start,end,submit_block,'ReportService submit')
# search ANY now includes category/evidence; add category list method.
s=replace_once(s,
'''            case ANY -> contains(entry.reporterName(), needle) || contains(entry.reporterUuid(), needle)\n                    || contains(entry.targetName(), needle) || contains(entry.targetUuid(), needle);\n''',
'''            case ANY -> contains(entry.reporterName(), needle) || contains(entry.reporterUuid(), needle)\n                    || contains(entry.targetName(), needle) || contains(entry.targetUuid(), needle)\n                    || contains(entry.category(), needle) || contains(entry.evidence(), needle);\n''','search any')
s=replace_once(s,
'''    public List<ReportEntry> recent(int limit, Status filter) {\n''',
'''    public List<ReportEntry> listByCategory(String rawCategory, Status filter) {\n        String category = normalizeCategory(rawCategory);\n        return list(filter).stream().filter(entry -> normalizeCategory(entry.category()).equals(category)).toList();\n    }\n\n    public List<ReportEntry> recent(int limit, Status filter) {\n''','listByCategory')
# readEntry adds category/evidence.
s=replace_once(s,
'''                data.getString(base + "target.name", "unknown"), data.getString(base + "target.uuid", ""),\n                data.getString(base + "reason", ""), data.getString(base + "world", "unknown"),\n''',
'''                data.getString(base + "target.name", "unknown"), data.getString(base + "target.uuid", ""),\n                normalizeCategory(data.getString(base + "category", "OTHER")), data.getString(base + "reason", ""),\n                data.getString(base + "evidence", ""), data.getString(base + "world", "unknown"),\n''','readEntry fields')
# notify/hook signatures.
start='    private void notifyStaff(int id, Player reporter, Player target, String reason) {'
end='    private boolean save() {'
notify_block=r'''    private void notifyStaff(int id, Player reporter, Player target, String category, String reason, String evidence) {
        String permission = plugin.getConfig().getString("integrations.report.staff-permission", "cdrmemberbook.staff.report");
        String message = "&8[&cREPORT #" + id + "&8] &7[&e" + category + "&7] &f" + reporter.getName()
                + " &7melaporkan &f" + target.getName() + "&7: &f" + reason
                + (evidence.isBlank() ? "" : " &8| &7Evidence: &f" + evidence);
        for (Player online : Bukkit.getOnlinePlayers()) if (permission == null || permission.isBlank() || online.hasPermission(permission)) online.sendMessage(Colors.legacy(message));
    }

    private void runConsoleHook(int id, Player reporter, Player target, String category, String reason, String evidence) {
        String template = plugin.getConfig().getString("integrations.report.console-command", "");
        if (template == null || template.isBlank()) return;
        String command = template.replace("%id%", Integer.toString(id)).replace("%reporter%", reporter.getName())
                .replace("%target%", target.getName()).replace("%category%", category)
                .replace("%reason%", reason).replace("%evidence%", evidence);
        if (command.startsWith("/")) command = command.substring(1);
        try { Bukkit.dispatchCommand(Bukkit.getConsoleSender(), command); }
        catch (Throwable throwable) { plugin.getLogger().warning("Report console hook failed: " + throwable.getMessage()); }
    }

'''
s=replace_between(s,start,end,notify_block,'notify/hook')
# record fields.
s=replace_once(s,
'''    public record ReportEntry(int id, Status status, String createdAt, String reporterName, String reporterUuid,\n                              String targetName, String targetUuid, String reason, String world,\n                              int x, int y, int z, String resolvedAt, String resolvedBy,\n''',
'''    public record ReportEntry(int id, Status status, String createdAt, String reporterName, String reporterUuid,\n                              String targetName, String targetUuid, String category, String reason, String evidence, String world,\n                              int x, int y, int z, String resolvedAt, String resolvedBy,\n''','record fields')
write(p,s)

# MenuHolder: extra types + context-aware Anvil constructor.
p='src/main/java/id/cadera/memberbook/gui/MenuHolder.java'; s=read(p)
s=replace_once(s,
'''        REPORT_CONFIRM,\n        REPORT_SUBMIT_PLAYER,\n        REPORT_SUBMIT_REASON,\n        REPORT_SUBMIT_CONFIRM\n''',
'''        REPORT_CONFIRM,\n        REPORT_SUBMIT_CATEGORY,\n        REPORT_SUBMIT_PLAYER,\n        REPORT_SUBMIT_REASON,\n        REPORT_SUBMIT_EVIDENCE,\n        REPORT_SUBMIT_CONFIRM\n''','holder types')
old='''    public MenuHolder(Type type, UUID targetId, String menuId, int page,\n                      InventoryType inventoryType, String title) {\n        this.type = type;\n        this.targetId = targetId;\n        this.menuId = menuId == null ? "main" : menuId;\n        this.page = Math.max(0, page);\n        this.context = "";\n        this.value = 0;\n        this.inventory = Bukkit.createInventory(this, inventoryType, title);\n    }\n'''
new='''    public MenuHolder(Type type, UUID targetId, String menuId, int page,\n                      InventoryType inventoryType, String title) {\n        this(type, targetId, menuId, page, "", 0, inventoryType, title);\n    }\n\n    public MenuHolder(Type type, UUID targetId, String menuId, int page, String context, int value,\n                      InventoryType inventoryType, String title) {\n        this.type = type;\n        this.targetId = targetId;\n        this.menuId = menuId == null ? "main" : menuId;\n        this.page = Math.max(0, page);\n        this.context = context == null ? "" : context;\n        this.value = value;\n        this.inventory = Bukkit.createInventory(this, inventoryType, title);\n    }\n'''
s=replace_once(s,old,new,'holder anvil context')
write(p,s)

# JavaMenuService: replace whole native submit block.
p='src/main/java/id/cadera/memberbook/gui/JavaMenuService.java'; s=read(p)
s=replace_once(s,
'''    private static final String REPORT_SUBMIT_SEND = "__report_submit_send";\n''',
'''    private static final String REPORT_SUBMIT_CATEGORY_PREFIX = "__report_submit_category:";\n    private static final String REPORT_SUBMIT_SEND = "__report_submit_send";\n''','java category constant')
s=replace_once(s,
'''            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);\n            case REPORT_SUBMIT_PLAYER -> handleReportSubmitPlayerClick(player, holder, clicked);\n            case REPORT_SUBMIT_REASON -> handleReportReasonClick(player, holder, event.getSlot());\n            case REPORT_SUBMIT_CONFIRM -> handlePlayerReportConfirmClick(player, holder, clicked);\n''',
'''            case REPORT_CONFIRM -> handleReportConfirmClick(player, holder, clicked);\n            case REPORT_SUBMIT_CATEGORY -> handleReportSubmitCategoryClick(player, holder, clicked);\n            case REPORT_SUBMIT_PLAYER -> handleReportSubmitPlayerClick(player, holder, clicked);\n            case REPORT_SUBMIT_REASON -> handleReportReasonClick(player, holder, event.getSlot());\n            case REPORT_SUBMIT_EVIDENCE -> handleReportEvidenceClick(player, holder, event.getSlot());\n            case REPORT_SUBMIT_CONFIRM -> handlePlayerReportConfirmClick(player, holder, clicked);\n''','java click switch')
s=replace_once(s,'showReportSubmitPlayerSelect(player, menu.id(), 0);','showReportCategorySelect(player, menu.id());','java report entry')
start='    // ---- Java Native Report Submit ----\n'
end='    // ---- Java Staff Report Center ----\n'
java_block=r'''    // ---- Java Native Report Submit ----

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
        if (holder.type() != MenuHolder.Type.REPORT_SUBMIT_REASON && holder.type() != MenuHolder.Type.REPORT_SUBMIT_EVIDENCE) return;
        AnvilInventory inventory = event.getInventory();
        inventory.setRepairCost(0);
        String value = inventory.getRenameText();
        ItemStack input = inventory.getItem(0);
        if (input == null || input.getType().isAir()) return;
        ItemStack result = input.clone();
        ItemMeta meta = result.getItemMeta();
        String fallback = holder.type() == MenuHolder.Type.REPORT_SUBMIT_REASON ? reportReasonPlaceholder() : reportEvidencePlaceholder();
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

'''
s=replace_between(s,start,end,java_block,'Java report submit block')
# Staff Java detail shows category/evidence.
s=replace_once(s,
'''        details.add("&7Target: &f" + entry.targetName());\n        details.add("&7Total report target: &f" + plugin.reports().countByTarget(entry.targetUuid(), null)\n''',
'''        details.add("&7Target: &f" + entry.targetName());\n        details.add("&7Kategori: &f" + plugin.reports().categoryLabel(entry.category()) + " &8(" + entry.category() + ")");\n        details.add("&7Total report target: &f" + plugin.reports().countByTarget(entry.targetUuid(), null)\n''','java detail category')
s=replace_once(s,
'''        details.add("&f" + shorten(entry.reason(), 80));\n''',
'''        details.add("&f" + shorten(entry.reason(), 80));\n        details.add("&7Evidence: &f" + (entry.evidence().isBlank() ? "-" : shorten(entry.evidence(), 80)));\n''','java detail evidence')
write(p,s)

# Bedrock report submit flow: category -> target -> reason -> evidence -> confirm.
p='src/main/java/id/cadera/memberbook/form/BedrockFormService.java'; s=read(p)
s=replace_once(s,'case "report" -> showReportPlayerSelect(player, menu.id());','case "report" -> showReportCategorySelect(player, menu.id());','bedrock report entry')
start='    private void showReportPlayerSelect(Player player, String returnMenuId) {'
end='    private boolean canManageReports(Player player) {'
bedrock_block=r'''    private void showReportCategorySelect(Player player, String returnMenuId) {
        if (!plugin.reports().categoriesEnabled()) { showReportPlayerSelect(player, returnMenuId, "OTHER"); return; }
        List<String> categories = plugin.reports().categories();
        SimpleForm.Builder builder = SimpleForm.builder().title("Kategori Laporan").content("Pilih jenis pelanggaran.");
        for (String category : categories) addButton(builder, plugin.reports().categoryLabel(category), "report", "textures/items/book_writable");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = categories.size();
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) { showConfiguredMenu(player, returnMenuId); return; }
            if (selected < 0 || selected >= categories.size()) return;
            showReportPlayerSelect(player, returnMenuId, categories.get(selected));
        })).build());
    }

    private void showReportPlayerSelect(Player player, String returnMenuId, String category) {
        List<PlayerChoice> choices = onlineTargets(player);
        SimpleForm.Builder builder = SimpleForm.builder().title("Lapor Player")
                .content(choices.isEmpty() ? "Tidak ada player lain yang online." : "Kategori: " + plugin.reports().categoryLabel(category) + "\nPilih player yang ingin dilaporkan.");
        for (PlayerChoice choice : choices) addButton(builder, choice.name(), "player", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = choices.size();
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) { showReportCategorySelect(player, returnMenuId); return; }
            if (selected < 0 || selected >= choices.size()) return;
            Player target = Bukkit.getPlayer(choices.get(selected).uuid());
            if (target == null) { plugin.message(player, "player-not-found"); showReportPlayerSelect(player, returnMenuId, category); return; }
            showReportReasonForm(player, target, returnMenuId, category);
        })).build());
    }

    private void showReportReasonForm(Player player, Player target, String returnMenuId, String category) {
        CustomForm form = CustomForm.builder().title("Lapor " + target.getName())
                .input("Alasan laporan", "contoh: penggunaan kill aura", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showReportPlayerSelect(player, returnMenuId, category)))
                .validResultHandler(response -> sync(() -> {
                    String reason = response.asInput(0);
                    int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
                    int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
                    if (reason == null || reason.trim().length() < min) { plugin.message(player, "report-reason-too-short", "%min%", Integer.toString(min)); showReportReasonForm(player, target, returnMenuId, category); return; }
                    if (reason.trim().length() > max) { plugin.message(player, "report-reason-too-long", "%max%", Integer.toString(max)); showReportReasonForm(player, target, returnMenuId, category); return; }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) { plugin.message(player, "player-not-found"); showReportPlayerSelect(player, returnMenuId, category); return; }
                    showReportEvidenceForm(player, currentTarget, returnMenuId, category, reason.trim());
                })).build();
        send(player, form);
    }

    private void showReportEvidenceForm(Player player, Player target, String returnMenuId, String category, String reason) {
        if (!plugin.getConfig().getBoolean("integrations.report.evidence.enabled", true)) { showReportConfirm(player, target, category, reason, "", returnMenuId); return; }
        CustomForm form = CustomForm.builder().title("Evidence • " + target.getName())
                .input("Evidence (opsional)", "teks atau https://link-bukti", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showReportReasonForm(player, target, returnMenuId, category)))
                .validResultHandler(response -> sync(() -> {
                    String evidence = response.asInput(0); if (evidence == null) evidence = ""; evidence = evidence.trim();
                    String validation = plugin.reports().validateEvidence(evidence);
                    if (!"ok".equals(validation)) { reportEvidenceError(player, validation); showReportEvidenceForm(player, target, returnMenuId, category, reason); return; }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) { plugin.message(player, "player-not-found"); showReportPlayerSelect(player, returnMenuId, category); return; }
                    showReportConfirm(player, currentTarget, category, reason, evidence, returnMenuId);
                })).build();
        send(player, form);
    }

    private void showReportConfirm(Player player, Player target, String category, String reason, String evidence, String returnMenuId) {
        String content = "Laporkan " + target.getName() + "?\n\nKategori: " + plugin.reports().categoryLabel(category)
                + "\nAlasan: " + reason + "\nEvidence: " + (evidence.isBlank() ? "-" : evidence);
        ModalForm form = ModalForm.builder().title("Konfirmasi Laporan").content(content)
                .button1("KIRIM LAPORAN").button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (!response.clickedFirst()) { showReportEvidenceForm(player, target, returnMenuId, category, reason); return; }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) { plugin.message(player, "player-not-found"); showReportPlayerSelect(player, returnMenuId, category); return; }
                    ReportService.SubmitResult result = plugin.reports().submit(player, currentTarget, category, reason, evidence);
                    if (result.success()) { plugin.message(player, "report-sent", "%id%", Integer.toString(result.id()), "%player%", currentTarget.getName()); showConfiguredMenu(player, returnMenuId); }
                    else if ("cooldown".equals(result.reasonCode())) { plugin.message(player, "report-cooldown", "%seconds%", Long.toString(result.waitSeconds())); showConfiguredMenu(player, returnMenuId); }
                    else if ("duplicate".equals(result.reasonCode())) { plugin.message(player, "report-duplicate", "%id%", Integer.toString(result.id()), "%seconds%", Long.toString(result.waitSeconds())); showConfiguredMenu(player, returnMenuId); }
                    else if ("self".equals(result.reasonCode())) { plugin.message(player, "cannot-report-self"); showReportPlayerSelect(player, returnMenuId, category); }
                    else if (result.reasonCode().startsWith("evidence")) { reportEvidenceError(player, result.reasonCode()); showReportEvidenceForm(player, currentTarget, returnMenuId, category, reason); }
                    else { plugin.message(player, "report-failed"); showConfiguredMenu(player, returnMenuId); }
                })).build();
        send(player, form);
    }

    private void reportEvidenceError(Player player, String code) {
        if ("evidence-required".equals(code)) plugin.message(player, "report-evidence-required");
        else if ("evidence-too-long".equals(code)) plugin.message(player, "report-evidence-too-long", "%max%", Integer.toString(Math.max(20, plugin.getConfig().getInt("integrations.report.evidence.max-length", 300))));
        else plugin.message(player, "report-evidence-invalid-link");
    }

'''
s=replace_between(s,start,end,bedrock_block,'Bedrock report block')
# Bedrock staff detail category/evidence.
s=replace_once(s,
'''                .append("Target: ").append(entry.targetName()).append('\\n')\n                .append("Total report target: ").append(plugin.reports().countByTarget(entry.targetUuid(), null))\n''',
'''                .append("Target: ").append(entry.targetName()).append('\\n')\n                .append("Kategori: ").append(plugin.reports().categoryLabel(entry.category())).append(" (").append(entry.category()).append(")\\n")\n                .append("Total report target: ").append(plugin.reports().countByTarget(entry.targetUuid(), null))\n''','bedrock detail category')
s=replace_once(s,
'''                .append("Alasan:\\n").append(entry.reason());\n''',
'''                .append("Alasan:\\n").append(entry.reason())\n                .append("\\nEvidence: ").append(entry.evidence().isBlank() ? "-" : entry.evidence());\n''','bedrock detail evidence')
write(p,s)

# Config v24 + defaults/messages.
p='src/main/resources/config.yml'; s=read(p)
s=replace_once(s,'# CdrMemberBook v1.9.6\nconfig-version: 23','# CdrMemberBook v1.9.7\nconfig-version: 24','config header')
marker='''    # Native Java player report submit. Tidak membutuhkan plugin /report eksternal.\n    java-submit:\n'''
insert='''    categories:\n      enabled: true\n      values: [CHEATING, GRIEFING, TOXIC, SCAM, BUG_ABUSE, OTHER]\n      labels:\n        CHEATING: 'Cheating / Hack'\n        GRIEFING: 'Griefing'\n        TOXIC: 'Toxic / Harassment'\n        SCAM: 'Scam'\n        BUG_ABUSE: 'Bug Abuse'\n        OTHER: 'Lainnya'\n    evidence:\n      enabled: true\n      optional: true\n      max-length: 300\n      require-http-url-if-link: true\n\n'''
s=replace_once(s,marker,insert+marker,'config category evidence')
s=replace_once(s,
'''      reason-material: PAPER\n''',
'''      reason-material: PAPER\n      evidence-title: '&8Lapor • Evidence'\n      evidence-placeholder: 'Evidence opsional...'\n''','java evidence config')
s=replace_once(s,
'''  report-reason-too-long: '&eAlasan laporan maksimal &f%max% &ekarakter.'\n''',
'''  report-reason-too-long: '&eAlasan laporan maksimal &f%max% &ekarakter.'\n  report-evidence-required: '&eEvidence wajib diisi untuk laporan ini.'\n  report-evidence-too-long: '&eEvidence maksimal &f%max% &ekarakter.'\n  report-evidence-invalid-link: '&cLink evidence hanya boleh memakai http:// atau https://.'\n''','messages evidence')
write(p,s)

# Config migration v24.
p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
s=replace_once(s,
'''        getConfig().set("config-version", 23);\n''',
'''        if (configVersion < 24) {\n            getConfig().set("integrations.report.categories.enabled", true);\n            getConfig().set("integrations.report.categories.values", java.util.List.of("CHEATING", "GRIEFING", "TOXIC", "SCAM", "BUG_ABUSE", "OTHER"));\n            getConfig().set("integrations.report.categories.labels.CHEATING", "Cheating / Hack");\n            getConfig().set("integrations.report.categories.labels.GRIEFING", "Griefing");\n            getConfig().set("integrations.report.categories.labels.TOXIC", "Toxic / Harassment");\n            getConfig().set("integrations.report.categories.labels.SCAM", "Scam");\n            getConfig().set("integrations.report.categories.labels.BUG_ABUSE", "Bug Abuse");\n            getConfig().set("integrations.report.categories.labels.OTHER", "Lainnya");\n            getConfig().set("integrations.report.evidence.enabled", true);\n            getConfig().set("integrations.report.evidence.optional", true);\n            getConfig().set("integrations.report.evidence.max-length", 300);\n            getConfig().set("integrations.report.evidence.require-http-url-if-link", true);\n            getConfig().set("integrations.report.java-submit.evidence-title", "&8Lapor • Evidence");\n            getConfig().set("integrations.report.java-submit.evidence-placeholder", "Evidence opsional...");\n        }\n\n        getConfig().set("config-version", 24);\n''','migration v24')
write(p,s)

# Admin report category filter + details/version.
p='src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'; s=read(p)
needle='''        if (args.length >= 2 && args[1].equalsIgnoreCase("player")) {\n'''
branch='''        if (args.length >= 2 && args[1].equalsIgnoreCase("category")) {\n            if (args.length < 3) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook reports category <category> [open|resolved|all] [page]")); return; }\n            String category = plugin.reports().normalizeCategory(args[2]);\n            if (!plugin.reports().categories().contains(category)) { sender.sendMessage(Colors.legacy("&cKategori tidak dikenal. Pilihan: &f" + String.join(", ", plugin.reports().categories()))); return; }\n            ReportService.Status filter = args.length >= 4 ? parseReportStatus(sender, args[3]) : null;\n            if (args.length >= 4 && !isReportStatusToken(args[3])) return;\n            int page = parsePositiveInt(args.length >= 5 ? args[4] : "1", 1);\n            sendReportPage(sender, plugin.reports().listByCategory(category, filter), page, "category " + category);\n            return;\n        }\n'''
s=replace_once(s,needle,branch+needle,'admin category branch')
s=replace_once(s,
'''                    + " &f" + e.reporterName() + " &8-> &f" + e.targetName() + " &8| &7" + shorten(e.reason(), 48)\n''',
'''                    + " &f" + e.reporterName() + " &8-> &f" + e.targetName() + " &8| &e[" + e.category() + "] &7" + shorten(e.reason(), 48)\n''','admin list category')
s=replace_once(s,
'''                sender.sendMessage(Colors.legacy("&7Alasan: &f" + e.reason()));\n''',
'''                sender.sendMessage(Colors.legacy("&7Kategori: &f" + plugin.reports().categoryLabel(e.category()) + " &8(" + e.category() + ")"));\n                sender.sendMessage(Colors.legacy("&7Alasan: &f" + e.reason()));\n                sender.sendMessage(Colors.legacy("&7Evidence: &f" + (e.evidence().isBlank() ? "-" : e.evidence())));\n''','admin view category evidence')
s=s.replace('&fv1.9.6','&fv1.9.7')
s=replace_once(s,'reports <search|recent|player> ...','reports <search|recent|player|category> ...','admin usage')
# Better report tab completion.
old='''        if (args[0].equalsIgnoreCase("reports")) {\n            if (args.length == 3) return List.of("open","resolved","all").stream().filter(v -> v.startsWith(args[2].toLowerCase(Locale.ROOT))).toList();\n            return List.of();\n        }\n'''
new='''        if (args[0].equalsIgnoreCase("reports")) {\n            if (args.length == 2) return List.of("search","recent","player","category").stream().filter(v -> v.startsWith(args[1].toLowerCase(Locale.ROOT))).toList();\n            if (args.length == 3 && args[1].equalsIgnoreCase("category")) return plugin.reports().categories().stream().filter(v -> v.toLowerCase(Locale.ROOT).startsWith(args[2].toLowerCase(Locale.ROOT))).toList();\n            if (args.length == 4 && args[1].equalsIgnoreCase("category")) return List.of("open","resolved","all").stream().filter(v -> v.startsWith(args[3].toLowerCase(Locale.ROOT))).toList();\n            if (args.length == 3 && !List.of("search","recent","player","category").contains(args[1].toLowerCase(Locale.ROOT))) return List.of("open","resolved","all").stream().filter(v -> v.startsWith(args[2].toLowerCase(Locale.ROOT))).toList();\n            return List.of();\n        }\n'''
s=replace_once(s,old,new,'admin tabs')
write(p,s)

# README/changelog.
p='README.md'; s=read(p); s=s.replace('# CdrMemberBook v1.9.6','# CdrMemberBook v1.9.7',1)
section='''\n## Report Categories & Evidence v1.9.7\n\nNative Java + Bedrock report sekarang memakai flow kategori -> target -> alasan -> evidence opsional -> konfirmasi. Default kategori: CHEATING, GRIEFING, TOXIC, SCAM, BUG_ABUSE, OTHER. Evidence menerima teks atau link; link berskema non-http/https ditolak dan panjangnya dibatasi config. Report lama tetap kompatibel dan dibaca sebagai kategori OTHER tanpa evidence. Staff dapat memfilter kategori melalui `/cdrmemberbook reports category <category> [open|resolved|all] [page]`. Placeholder console hook baru: `%category%` dan `%evidence%`.\n'''
s += section; write(p,s)
p='CHANGELOG.md'; s=read(p)
entry='''## 1.9.7 - Report Categories & Evidence\n\n- Added configurable report categories shared by Java and Bedrock native submit flows.\n- Added optional evidence text/link with length and URL-scheme validation.\n- Persisted category/evidence in reports.yml while keeping old reports backward compatible as OTHER/no evidence.\n- Added category/evidence to staff notifications, console hook placeholders, Java/Bedrock details, audit context and admin output.\n- Added `/cdrmemberbook reports category <category> [open|resolved|all] [page]`.\n- Java flow is now category -> target -> reason anvil -> evidence anvil -> confirmation.\n- Bedrock flow is now category -> target -> reason -> evidence -> confirmation.\n- Config migrated to version 24.\n\n'''
s=replace_once(s,'# Changelog\n\n','# Changelog\n\n'+entry,'changelog'); write(p,s)
print('v1.9.7 patch applied')
