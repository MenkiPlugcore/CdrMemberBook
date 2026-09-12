from pathlib import Path
import re

root = Path('.')

def read(p): return (root / p).read_text()
def write(p,s): (root / p).write_text(s)
def repl(s, old, new, label):
    if old not in s:
        raise SystemExit(f'pattern not found: {label}')
    return s.replace(old, new, 1)

# versions
p='pom.xml'; s=read(p); s=repl(s,'<version>1.9.2</version>','<version>1.9.3</version>','pom version'); write(p,s)
p='src/main/resources/plugin.yml'; s=read(p); s=repl(s,"version: '1.9.2'","version: '1.9.3'",'plugin version'); write(p,s)

# Menu type + availability
p='src/main/java/id/cadera/memberbook/menu/MenuConfigService.java'; s=read(p)
s=repl(s,
'private static final Set<String> KNOWN_TYPES = Set.of("command", "teleport", "homes", "pay", "trade", "report", "submenu", "close");',
'private static final Set<String> KNOWN_TYPES = Set.of("command", "teleport", "homes", "pay", "trade", "report", "report-center", "submenu", "close");',
'known types')
s=repl(s,
'''            case "report" -> (plugin.reports()!=null && plugin.reports().enabled() && plugin.forms()!=null && plugin.forms().isBedrock(player)) ? new Availability(true,"ok","native-report") : availableCommand(button.command());\n            case "command" ->''',
'''            case "report" -> (plugin.reports()!=null && plugin.reports().enabled() && plugin.forms()!=null && plugin.forms().isBedrock(player)) ? new Availability(true,"ok","native-report") : availableCommand(button.command());\n            case "report-center" -> {\n                if (plugin.reports() == null || !plugin.reports().enabled())\n                    yield new Availability(false,"report-disabled","native report disabled");\n                if (!plugin.getConfig().getBoolean("integrations.report.center.enabled", true))\n                    yield new Availability(false,"report-center-disabled","center disabled");\n                if (plugin.forms() == null || !plugin.forms().isBedrock(player))\n                    yield new Availability(false,"bedrock-only","Report Center Bedrock only");\n                yield new Availability(true,"ok","native-report-center");\n            }\n            case "command" ->''',
'report center availability')
write(p,s)

# Bedrock Report Center
p='src/main/java/id/cadera/memberbook/form/BedrockFormService.java'; s=read(p)
s=repl(s,
'''            case "report" -> showReportPlayerSelect(player, menu.id());\n            case "submenu" -> {''',
'''            case "report" -> showReportPlayerSelect(player, menu.id());\n            case "report-center" -> showReportCenter(player, menu.id());\n            case "submenu" -> {''',
'bedrock handler')

marker='''    private void showTradeMenu(Player player, String returnMenuId) {\n'''
insert=r'''    private boolean canManageReports(Player player) {
        if (player == null || !player.isOnline()) return false;
        if (!plugin.getConfig().getBoolean("integrations.report.center.enabled", true)) return false;
        String permission = plugin.getConfig().getString("integrations.report.staff-permission", "cdrmemberbook.staff.report");
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }

    private boolean ensureReportStaff(Player player, String returnMenuId) {
        if (canManageReports(player)) return true;
        plugin.message(player, "no-permission");
        if (player.isOnline()) showConfiguredMenu(player, returnMenuId == null ? "main" : returnMenuId);
        return false;
    }

    private void showReportCenter(Player player, String returnMenuId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        int open = plugin.reports().count(ReportService.Status.OPEN);
        int resolved = plugin.reports().count(ReportService.Status.RESOLVED);
        int all = open + resolved;

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Report Center")
                .content("Kelola laporan langsung dari Member Book.\nOPEN: " + open
                        + " | RESOLVED: " + resolved + " | TOTAL: " + all);
        addButton(builder, "Open Reports (" + open + ")", "report", "textures/items/book_writable");
        addButton(builder, "Resolved Reports (" + resolved + ")", "report", "textures/items/book_written");
        addButton(builder, "Semua Reports (" + all + ")", "report", "textures/items/book_normal");
        addButton(builder, "Refresh", "refresh", "textures/items/compass_item");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!ensureReportStaff(player, returnMenuId)) return;
            switch (response.clickedButtonId()) {
                case 0 -> showReportList(player, returnMenuId, ReportService.Status.OPEN, 1);
                case 1 -> showReportList(player, returnMenuId, ReportService.Status.RESOLVED, 1);
                case 2 -> showReportList(player, returnMenuId, null, 1);
                case 3 -> showReportCenter(player, returnMenuId);
                case 4 -> showConfiguredMenu(player, returnMenuId);
                default -> { }
            }
        })).build());
    }

    private void showReportList(Player player, String returnMenuId, ReportService.Status filter, int requestedPage) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        List<ReportService.ReportEntry> entries = plugin.reports().list(filter);
        int pageSize = Math.max(1, Math.min(20,
                plugin.getConfig().getInt("integrations.report.center.page-size", 8)));
        int pages = Math.max(1, (entries.size() + pageSize - 1) / pageSize);
        int currentPage = Math.max(1, Math.min(requestedPage, pages));
        int start = (currentPage - 1) * pageSize;
        int end = Math.min(entries.size(), start + pageSize);
        int entryCount = end - start;
        boolean hasPrev = currentPage > 1;
        boolean hasNext = currentPage < pages;
        int prevIndex = hasPrev ? entryCount : -1;
        int nextIndex = hasNext ? entryCount + (hasPrev ? 1 : 0) : -1;
        int centerIndex = entryCount + (hasPrev ? 1 : 0) + (hasNext ? 1 : 0);

        String filterName = filter == null ? "ALL" : filter.name();
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Reports • " + filterName)
                .content(entries.isEmpty() ? "Belum ada report pada filter ini."
                        : "Halaman " + currentPage + "/" + pages + " • Total " + entries.size());

        for (int i = start; i < end; i++) {
            ReportService.ReportEntry entry = entries.get(i);
            String state = entry.status() == ReportService.Status.OPEN ? "OPEN" : "RESOLVED";
            String label = "#" + entry.id() + " • " + entry.targetName()
                    + "\n" + state + " • oleh " + entry.reporterName();
            addButton(builder, label, "report", entry.status() == ReportService.Status.OPEN
                    ? "textures/items/book_writable" : "textures/items/book_written");
        }
        if (hasPrev) addButton(builder, "Halaman Sebelumnya", "back", "textures/items/arrow");
        if (hasNext) addButton(builder, "Halaman Berikutnya", "next", "textures/items/arrow");
        addButton(builder, "Kembali ke Report Center", "back", "textures/items/compass_item");

        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!ensureReportStaff(player, returnMenuId)) return;
            int selected = response.clickedButtonId();
            if (selected >= 0 && selected < entryCount) {
                showReportDetail(player, returnMenuId, filter, currentPage, entries.get(start + selected).id());
                return;
            }
            if (selected == prevIndex) {
                showReportList(player, returnMenuId, filter, currentPage - 1);
                return;
            }
            if (selected == nextIndex) {
                showReportList(player, returnMenuId, filter, currentPage + 1);
                return;
            }
            if (selected == centerIndex) showReportCenter(player, returnMenuId);
        })).build());
    }

    private void showReportDetail(Player player, String returnMenuId, ReportService.Status filter,
                                  int page, int reportId) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        ReportService.ReportEntry entry = plugin.reports().get(reportId);
        if (entry == null) {
            plugin.message(player, "report-not-found", "%id%", Integer.toString(reportId));
            showReportList(player, returnMenuId, filter, page);
            return;
        }

        StringBuilder content = new StringBuilder()
                .append("Status: ").append(entry.status()).append('\n')
                .append("Reporter: ").append(entry.reporterName()).append('\n')
                .append("Target: ").append(entry.targetName()).append('\n')
                .append("Waktu: ").append(entry.createdAt()).append('\n')
                .append("Lokasi: ").append(entry.world()).append(' ')
                .append(entry.x()).append(',').append(entry.y()).append(',').append(entry.z()).append("\n\n")
                .append("Alasan:\n").append(entry.reason());
        if (entry.status() == ReportService.Status.RESOLVED) {
            content.append("\n\nResolved by: ").append(entry.resolvedBy())
                    .append("\nResolved at: ").append(entry.resolvedAt());
        }

        boolean allowDelete = plugin.getConfig().getBoolean("integrations.report.center.allow-delete", true);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Report #" + entry.id())
                .content(content.toString());
        if (entry.status() == ReportService.Status.OPEN) {
            addButton(builder, "Resolve Report", "confirm", "textures/items/emerald");
        } else {
            addButton(builder, "Reopen Report", "refresh", "textures/items/compass_item");
        }
        if (allowDelete) addButton(builder, "Hapus Report", "delete", "textures/items/barrier");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int deleteIndex = allowDelete ? 1 : -1;
        int backIndex = allowDelete ? 2 : 1;
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!ensureReportStaff(player, returnMenuId)) return;
            int selected = response.clickedButtonId();
            if (selected == 0) {
                showReportActionConfirm(player, returnMenuId, filter, page, reportId,
                        entry.status() == ReportService.Status.OPEN ? "resolve" : "reopen");
                return;
            }
            if (selected == deleteIndex) {
                showReportActionConfirm(player, returnMenuId, filter, page, reportId, "delete");
                return;
            }
            if (selected == backIndex) showReportList(player, returnMenuId, filter, page);
        })).build());
    }

    private void showReportActionConfirm(Player player, String returnMenuId, ReportService.Status filter,
                                         int page, int reportId, String action) {
        if (!ensureReportStaff(player, returnMenuId)) return;
        ReportService.ReportEntry entry = plugin.reports().get(reportId);
        if (entry == null) {
            plugin.message(player, "report-not-found", "%id%", Integer.toString(reportId));
            showReportList(player, returnMenuId, filter, page);
            return;
        }
        String title;
        String text;
        String confirm;
        switch (action) {
            case "resolve" -> { title = "Resolve Report"; text = "Tandai report #" + reportId + " sebagai RESOLVED?"; confirm = "RESOLVE"; }
            case "reopen" -> { title = "Reopen Report"; text = "Buka kembali report #" + reportId + " sebagai OPEN?"; confirm = "REOPEN"; }
            case "delete" -> { title = "Hapus Report"; text = "Hapus permanen report #" + reportId + "?\nTindakan ini tidak dapat dibatalkan."; confirm = "HAPUS"; }
            default -> { showReportDetail(player, returnMenuId, filter, page, reportId); return; }
        }

        ModalForm form = ModalForm.builder()
                .title(title)
                .content(text)
                .button1(confirm)
                .button2("BATAL")
                .validResultHandler(response -> sync(() -> {
                    if (!ensureReportStaff(player, returnMenuId)) return;
                    if (!response.clickedFirst()) {
                        showReportDetail(player, returnMenuId, filter, page, reportId);
                        return;
                    }
                    boolean success = switch (action) {
                        case "resolve" -> plugin.reports().resolve(reportId, player.getName());
                        case "reopen" -> plugin.reports().reopen(reportId, player.getName());
                        case "delete" -> plugin.reports().delete(reportId);
                        default -> false;
                    };
                    if (!success) {
                        plugin.message(player, "report-action-failed");
                        showReportList(player, returnMenuId, filter, page);
                        return;
                    }
                    switch (action) {
                        case "resolve" -> plugin.message(player, "report-resolved", "%id%", Integer.toString(reportId));
                        case "reopen" -> plugin.message(player, "report-reopened", "%id%", Integer.toString(reportId));
                        case "delete" -> plugin.message(player, "report-deleted", "%id%", Integer.toString(reportId));
                        default -> { }
                    }
                    if ("delete".equals(action)) showReportList(player, returnMenuId, filter, page);
                    else showReportDetail(player, returnMenuId, filter, page, reportId);
                }))
                .build();
        send(player, form);
    }

'''
s=repl(s,marker,insert+marker,'report center methods')
write(p,s)

# Java explicitly rejects native report center if someone disables hide-unavailable.
p='src/main/java/id/cadera/memberbook/gui/JavaMenuService.java'; s=read(p)
s=repl(s,
'''            case "teleport" -> showPlayerSelect(player, menu.id(), 0);\n            case "submenu" -> {''',
'''            case "teleport" -> showPlayerSelect(player, menu.id(), 0);\n            case "report-center" -> plugin.message(player, "feature-unavailable");\n            case "submenu" -> {''',
'java report center guard')
write(p,s)

# Config/version/default button/messages.
p='src/main/resources/config.yml'; s=read(p)
s=repl(s,'# CdrMemberBook v1.9.2\nconfig-version: 19','# CdrMemberBook v1.9.3\nconfig-version: 20','config header')
s=repl(s,
'''    # Optional hook setelah report tersimpan. Placeholder: %id%, %reporter%, %target%, %reason%.\n    console-command: ''\n''',
'''    # Optional hook setelah report tersimpan. Placeholder: %id%, %reporter%, %target%, %reason%.\n    console-command: ''\n    # Native Bedrock staff Report Center. Java staff UI akan ditambahkan terpisah.\n    center:\n      enabled: true\n      page-size: 8\n      allow-delete: true\n''',
'report center config')
s=repl(s,
'''#   trade    = native Bedrock AxTrade send/accept/deny/toggle flow\n#   submenu  = open a submenu from menu.submenus\n''',
'''#   trade    = native Bedrock AxTrade send/accept/deny/toggle flow\n#   report-center = native Bedrock staff Report Center\n#   submenu  = open a submenu from menu.submenus\n''',
'button type comment')
s=repl(s,
'''      barter:\n        enabled: true\n''',
'''      report-center:\n        enabled: true\n        name: '&cReport Center'\n        type: report-center\n        order: 115\n        icon: textures/items/book_written\n        java-material: KNOWLEDGE_BOOK\n        permission: 'cdrmemberbook.staff.report'\n        conditions:\n          platform: BEDROCK\n        lore:\n        - '&7Kelola laporan OPEN/RESOLVED.'\n        - '&7Khusus staff Bedrock.'\n\n      barter:\n        enabled: true\n''',
'default report center button')
s=repl(s,
'''  report-failed: '&cLaporan tidak dapat dikirim. Coba lagi atau hubungi staff.'\n  config-reloaded:''',
'''  report-failed: '&cLaporan tidak dapat dikirim. Coba lagi atau hubungi staff.'\n  report-not-found: '&cReport &f#%id% &ctidak ditemukan atau sudah dihapus.'\n  report-resolved: '&aReport &f#%id% &aberhasil ditandai RESOLVED.'\n  report-reopened: '&eReport &f#%id% &edibuka kembali sebagai OPEN.'\n  report-deleted: '&aReport &f#%id% &aberhasil dihapus.'\n  report-action-failed: '&cPerubahan report gagal disimpan. Cek console/storage lalu coba lagi.'\n  config-reloaded:''',
'report center messages')
write(p,s)

# Plugin migration/startup.
p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
s=repl(s,'getLogger().info("CdrMemberBook v1.9.2 enabled.");','getLogger().info("CdrMemberBook v1.9.3 enabled.");','startup version')
s=repl(s,
'''        getConfig().set("config-version", 19);\n        saveConfig();\n''',
'''        if (configVersion < 20) {\n            getConfig().set("integrations.report.center.enabled", true);\n            getConfig().set("integrations.report.center.page-size", 8);\n            getConfig().set("integrations.report.center.allow-delete", true);\n        }\n\n        getConfig().set("config-version", 20);\n        saveConfig();\n''',
'config migration 20')
write(p,s)

# README/changelog
p='README.md'; s=read(p); s=re.sub(r'^# CdrMemberBook v1\.9\.2','# CdrMemberBook v1.9.3',s,count=1,flags=re.M)
section='''\n## Bedrock Staff Report Center v1.9.3\n\nStaff Bedrock dengan permission `cdrmemberbook.staff.report` mendapat tombol `Report Center` di Member Book. Center menyediakan filter OPEN/RESOLVED/ALL, pagination, detail laporan, Resolve, Reopen, Delete dengan konfirmasi, dan refresh tanpa command. Tombol ini sengaja disembunyikan dari Java sampai Java staff UI dibuat pada update terpisah.\n'''
if '## Bedrock Staff Report Center v1.9.3' not in s: s += section
write(p,s)
p='CHANGELOG.md'; s=read(p)
entry='''\n## 1.9.3 - Bedrock Staff Report Center\n\n- Added native Bedrock `Report Center` for staff permission `cdrmemberbook.staff.report`.\n- Added OPEN / RESOLVED / ALL filters with pagination and refresh.\n- Added report detail view with reporter, target, reason, timestamp, location and resolution metadata.\n- Added native Resolve, Reopen and Delete actions with confirmation forms.\n- Added `report-center` menu button type and default Bedrock-only staff button.\n- Kept Java Report Center hidden for a dedicated follow-up Java UI update.\n\n'''
if '## 1.9.3 - Bedrock Staff Report Center' not in s: s=repl(s,'# Changelog\n','# Changelog\n'+entry,'changelog')
write(p,s)
