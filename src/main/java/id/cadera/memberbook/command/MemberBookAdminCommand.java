package id.cadera.memberbook.command;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.item.MemberBookService;
import id.cadera.memberbook.menu.MenuConfigService;
import id.cadera.memberbook.report.ReportService;
import id.cadera.memberbook.util.Colors;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class MemberBookAdminCommand implements CommandExecutor, TabCompleter {
    private static final String PERMISSION = "cdrmemberbook.admin.memberbook";
    private final CdrMemberBookPlugin plugin;

    public MemberBookAdminCommand(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (!sender.hasPermission(PERMISSION)) {
            sender.sendMessage(Colors.legacy("&cKamu tidak punya izin untuk command ini."));
            return true;
        }
        if (args.length == 0) { sendUsage(sender, label); return true; }
        String action = args[0].toLowerCase(Locale.ROOT);
        if (action.equals("reports")) { handleReports(sender, args); return true; }
        if (action.equals("report")) { handleReport(sender, args); return true; }
        if (action.equals("health")) { sendHealth(sender); return true; }
        if (args.length < 2) { sendUsage(sender, label); return true; }

        Player target = Bukkit.getPlayerExact(args[1]);
        if (target == null) {
            sender.sendMessage(Colors.legacy("&cPlayer &f" + args[1] + " &ctidak ditemukan atau sedang offline."));
            return true;
        }
        MemberBookService service = plugin.memberBook();
        switch (action) {
            case "give" -> {
                if (!service.isEligibleForBook(target)) { sender.sendMessage(Colors.legacy("&e" + target.getName() + " &cbukan player yang eligible menerima Member Book.")); return true; }
                boolean success = service.forceGive(target);
                sender.sendMessage(Colors.legacy(success ? "&aMember Book dipastikan tersedia untuk &f" + target.getName() + "&a."
                        : "&eInventory/cursor &f" + target.getName() + " &epenuh."));
            }
            case "remove" -> {
                int removed = service.forceRemove(target);
                sender.sendMessage(Colors.legacy("&aMenghapus &f" + removed + " &acopy Member Book dari &f" + target.getName() + "&a."));
            }
            case "fix" -> {
                if (!service.isEligibleForBook(target)) { sender.sendMessage(Colors.legacy("&e" + target.getName() + " &cbukan player yang eligible menerima Member Book.")); return true; }
                sender.sendMessage(Colors.legacy(service.forceRepair(target)
                        ? "&aMember Book &f" + target.getName() + " &aberhasil diperiksa dan diperbaiki."
                        : "&eRecovery belum bisa menaruh buku karena inventory/cursor penuh."));
            }
            case "refresh" -> sender.sendMessage(Colors.legacy(service.refreshDynamicBook(target)
                    ? "&aDynamic Member Book &f" + target.getName() + " &aberhasil direfresh."
                    : "&eTidak ada Member Book aktif yang bisa direfresh."));
            case "status" -> sendStatus(sender, target, service.inspect(target));
            case "menudebug" -> sendMenuDebug(sender, target, args.length >= 3 ? args[2] : "main");
            case "tutorialreset" -> {
                plugin.tutorial().reset(target);
                sender.sendMessage(Colors.legacy("&aFirst Join Tutorial di-reset untuk &f" + target.getName() + "&a."));
            }
            case "tutorialshow" -> {
                if (!plugin.tutorial().canShow(target)) { sender.sendMessage(Colors.legacy("&eTutorial hanya bisa ditampilkan ke player yang eligible.")); return true; }
                plugin.tutorial().showNow(target);
                sender.sendMessage(Colors.legacy("&aTutorial ditampilkan ke &f" + target.getName() + "&a."));
            }
            default -> sendUsage(sender, label);
        }
        return true;
    }

    private void sendStatus(CommandSender sender, Player target, MemberBookService.BookStatus status) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook Status &8- &f" + target.getName()));
        sender.sendMessage(Colors.legacy("&7Mode: &f" + status.mode() + (status.configuredModeValid() ? "" : " &c(config invalid -> fallback)")));
        sender.sendMessage(Colors.legacy("&7Platform: &f" + (status.bedrock() ? "Bedrock" : "Java") + " &8| &7Eligible: &f" + status.eligible()));
        sender.sendMessage(Colors.legacy("&7Copies: &f" + status.visibleCopies() + " &8(inv=" + status.inventoryCopies() + ", cursor=" + status.cursorBook() + ", external=" + status.externalCopies() + ")"));
        sender.sendMessage(Colors.legacy("&7Reserved slot: &f" + status.reservedSlot() + " &8| &7Book in slot: &f" + status.bookInReservedSlot()));
        sender.sendMessage(Colors.legacy("&7Recovery: &f" + status.recoveryEnabled() + " &8| &7Suppressed: &f" + status.recoverySuppressed() + " &8| &7Fixed return pending: &f" + status.fixedReturnPending()));
        sender.sendMessage(Colors.legacy("&7External protection: &f" + status.externalStorageProtected() + " &8| &7Drop protection: &f" + status.dropProtected() + " &8| &7Dynamic: &f" + status.dynamicEnabled()));
    }

    private void sendMenuDebug(CommandSender sender, Player target, String menuId) {
        MenuConfigService.MenuDefinition menu = plugin.menus().getMenu(menuId);
        if (menu == null) { sender.sendMessage(Colors.legacy("&cMenu tidak ditemukan: &f" + menuId)); return; }
        boolean hidePerm = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);
        sender.sendMessage(Colors.legacy("&dMenu Debug &8- &f" + target.getName() + " &8/ &f" + menu.id()));
        for (MenuConfigService.MenuButton button : menu.buttons()) {
            boolean permission = plugin.menus().canUse(target, button);
            MenuConfigService.Availability available = plugin.menus().availability(target, button);
            boolean visible = (!hidePerm || permission) && (!hideUnavailable || available.available());
            sender.sendMessage(Colors.legacy((visible ? "&a✔ " : "&c✘ ") + "&f" + button.key()
                    + " &8| &7type=&f" + button.type() + " &8| &7perm=&f" + permission
                    + " &8| &7availability=&f" + available.code() + (available.detail().isBlank() ? "" : " &8(" + available.detail() + ")")));
        }
    }

    private void handleReports(CommandSender sender, String[] args) {
        if (args.length >= 2 && args[1].equalsIgnoreCase("search")) {
            if (args.length < 4) {
                sender.sendMessage(Colors.legacy("&f/cdrmemberbook reports search <reporter|target|any> <player> [open|resolved|all] [page]"));
                return;
            }
            ReportService.SearchField field = plugin.reports().parseSearchField(args[2]);
            if (field == null) { sender.sendMessage(Colors.legacy("&cField harus reporter/target/any.")); return; }
            ReportService.Status filter = parseReportStatus(sender, args.length >= 5 ? args[4] : "all");
            if (args.length >= 5 && !isReportStatusToken(args[4])) return;
            int page = parsePositiveInt(args.length >= 6 ? args[5] : "1", 1);
            sendReportPage(sender, plugin.reports().search(args[3], field, filter), page,
                    "search " + field + "=" + args[3]);
            return;
        }
        if (args.length >= 2 && args[1].equalsIgnoreCase("recent")) {
            int limit = parsePositiveInt(args.length >= 3 ? args[2] : Integer.toString(plugin.getConfig().getInt("integrations.report.recent-limit", 10)), 10);
            sendReportPage(sender, plugin.reports().recent(limit, null), 1, "recent");
            return;
        }
        if (args.length >= 2 && args[1].equalsIgnoreCase("category")) {
            if (args.length < 3) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook reports category <category> [open|resolved|all] [page]")); return; }
            String category = plugin.reports().normalizeCategory(args[2]);
            if (!plugin.reports().categories().contains(category)) { sender.sendMessage(Colors.legacy("&cKategori tidak dikenal. Pilihan: &f" + String.join(", ", plugin.reports().categories()))); return; }
            ReportService.Status filter = args.length >= 4 ? parseReportStatus(sender, args[3]) : null;
            if (args.length >= 4 && !isReportStatusToken(args[3])) return;
            int page = parsePositiveInt(args.length >= 5 ? args[4] : "1", 1);
            sendReportPage(sender, plugin.reports().listByCategory(category, filter), page, "category " + category);
            return;
        }
        if (args.length >= 2 && args[1].equalsIgnoreCase("player")) {
            if (args.length < 3) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook reports player <name>")); return; }
            String q = args[2];
            sender.sendMessage(Colors.legacy("&dReport Stats &8- &f" + q));
            sender.sendMessage(Colors.legacy("&7Sebagai reporter: &f" + plugin.reports().countByReporter(q, null)
                    + " &8| &7Sebagai target: &f" + plugin.reports().countByTarget(q, null)
                    + " &8(open=&f" + plugin.reports().countByTarget(q, ReportService.Status.OPEN) + "&8)"));
            sendReportPage(sender, plugin.reports().search(q, ReportService.SearchField.ANY, null), 1, "player " + q);
            return;
        }
        int page = 1;
        if (args.length >= 2) try { page = Math.max(1, Integer.parseInt(args[1])); } catch (NumberFormatException ignored) { }
        ReportService.Status filter = null;
        if (args.length >= 3) {
            filter = parseReportStatus(sender, args[2]);
            if (!isReportStatusToken(args[2])) return;
        }
        sendReportPage(sender, plugin.reports().list(filter), page, filter == null ? "all" : filter.name());
    }

    private ReportService.Status parseReportStatus(CommandSender sender, String raw) {
        if (raw == null || raw.isBlank() || raw.equalsIgnoreCase("all")) return null;
        try { return ReportService.Status.valueOf(raw.toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ex) {
            sender.sendMessage(Colors.legacy("&cStatus harus open/resolved/all."));
            return null;
        }
    }

    private boolean isReportStatusToken(String raw) {
        if (raw == null || raw.isBlank()) return true;
        return raw.equalsIgnoreCase("all") || raw.equalsIgnoreCase("open") || raw.equalsIgnoreCase("resolved");
    }

    private int parsePositiveInt(String raw, int fallback) {
        try { return Math.max(1, Integer.parseInt(raw)); }
        catch (NumberFormatException ignored) { return Math.max(1, fallback); }
    }

    private void sendReportPage(CommandSender sender, List<ReportService.ReportEntry> entries, int requestedPage, String label) {
        int size = Math.max(1, plugin.getConfig().getInt("integrations.report.admin-page-size", 8));
        int pages = Math.max(1, (entries.size() + size - 1) / size);
        int page = Math.max(1, Math.min(requestedPage, pages));
        int start = (page - 1) * size;
        int end = Math.min(entries.size(), start + size);
        sender.sendMessage(Colors.legacy("&dCdrMemberBook Reports &8- &f" + page + "/" + pages + " &8| &7" + label
                + " &8| &7total=&f" + entries.size() + " &8| &7open=&f" + plugin.reports().count(ReportService.Status.OPEN)));
        if (entries.isEmpty()) { sender.sendMessage(Colors.legacy("&7Tidak ada report.")); return; }
        for (int i = start; i < end; i++) {
            ReportService.ReportEntry e = entries.get(i);
            sender.sendMessage(Colors.legacy((e.status() == ReportService.Status.OPEN ? "&c" : "&a") + "#" + e.id()
                    + " &f" + e.reporterName() + " &8-> &f" + e.targetName() + " &8| &e[" + e.category() + "] &7" + shorten(e.reason(), 48)
                    + (e.notes().isEmpty() ? "" : " &8| &e" + e.notes().size() + " note")));
        }
    }

    private void handleReport(CommandSender sender, String[] args) {
        if (args.length < 3) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook report <view|resolve|reopen|delete|note|audit> <id> [text]")); return; }
        int id;
        try { id = Integer.parseInt(args[2]); } catch (NumberFormatException ex) { sender.sendMessage(Colors.legacy("&cID report tidak valid.")); return; }
        if (id <= 0) { sender.sendMessage(Colors.legacy("&cID report harus lebih dari 0.")); return; }
        String action = args[1].toLowerCase(Locale.ROOT);
        ReportService.ReportEntry e = plugin.reports().get(id);
        if (e == null) { sender.sendMessage(Colors.legacy("&cReport #" + id + " tidak ditemukan.")); return; }
        String staff = sender.getName();
        switch (action) {
            case "view" -> {
                sender.sendMessage(Colors.legacy("&dReport #" + e.id() + " &8- &f" + e.status()));
                sender.sendMessage(Colors.legacy("&7Reporter: &f" + e.reporterName() + " &8(" + e.reporterUuid() + ")"));
                sender.sendMessage(Colors.legacy("&7Target: &f" + e.targetName() + " &8(" + e.targetUuid() + ") &8| &7Total target reports: &f" + plugin.reports().countByTarget(e.targetUuid(), null)));
                sender.sendMessage(Colors.legacy("&7Kategori: &f" + plugin.reports().categoryLabel(e.category()) + " &8(" + e.category() + ")"));
                sender.sendMessage(Colors.legacy("&7Alasan: &f" + e.reason()));
                sender.sendMessage(Colors.legacy("&7Evidence: &f" + (e.evidence().isBlank() ? "-" : e.evidence())));
                sender.sendMessage(Colors.legacy("&7Waktu: &f" + e.createdAt() + " &8| &7Lokasi: &f" + e.world() + " " + e.x() + "," + e.y() + "," + e.z()));
                if (e.status() == ReportService.Status.RESOLVED) sender.sendMessage(Colors.legacy("&7Resolved: &f" + e.resolvedBy() + " &8@ &f" + e.resolvedAt()));
                if (!e.notes().isEmpty()) {
                    ReportService.StaffNote note = e.notes().get(e.notes().size() - 1);
                    sender.sendMessage(Colors.legacy("&7Latest note: &e" + note.staff() + "&8: &f" + note.text()));
                }
                sender.sendMessage(Colors.legacy("&7Audit entries: &f" + e.audit().size() + " &8| &7Notes: &f" + e.notes().size()));
            }
            case "resolve" -> sender.sendMessage(Colors.legacy(plugin.reports().resolve(id, staff)
                    ? "&aReport #" + id + " ditandai RESOLVED." : "&cGagal menyimpan perubahan report #" + id + "."));
            case "reopen" -> sender.sendMessage(Colors.legacy(plugin.reports().reopen(id, staff)
                    ? "&eReport #" + id + " dibuka kembali." : "&cGagal menyimpan perubahan report #" + id + "."));
            case "delete" -> sender.sendMessage(Colors.legacy(plugin.reports().delete(id)
                    ? "&aReport #" + id + " dihapus." : "&cGagal menghapus report #" + id + "."));
            case "note" -> {
                if (args.length < 4) { sender.sendMessage(Colors.legacy("&f/cdrmemberbook report note " + id + " <catatan staff>")); return; }
                String note = String.join(" ", java.util.Arrays.copyOfRange(args, 3, args.length));
                sender.sendMessage(Colors.legacy(plugin.reports().addNote(id, staff, note)
                        ? "&aCatatan staff ditambahkan ke report #" + id + "." : "&cGagal menambah catatan report #" + id + "."));
            }
            case "audit" -> {
                sender.sendMessage(Colors.legacy("&dAudit Report #" + id + " &8- &7" + e.audit().size() + " event"));
                int start = Math.max(0, e.audit().size() - 10);
                for (int i = start; i < e.audit().size(); i++) {
                    ReportService.AuditEntry audit = e.audit().get(i);
                    sender.sendMessage(Colors.legacy("&8- &f" + audit.action() + " &7by &f" + audit.actor() + " &8| &7" + shorten(audit.detail(), 72) + " &8@ " + audit.at()));
                }
            }
            default -> sender.sendMessage(Colors.legacy("&cAction report harus view/resolve/reopen/delete/note/audit."));
        }
    }

    private void sendHealth(CommandSender sender) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook Health &8- &fv1.9.8"));
        sender.sendMessage(Colors.legacy("&7Config version: &f" + plugin.getConfig().getInt("config-version", -1)
                + " &8| &7Actions: &f" + plugin.getConfig().getBoolean("menu.actions.enabled", true)));
        sender.sendMessage(Colors.legacy("&7Floodgate: &f" + Bukkit.getPluginManager().isPluginEnabled("floodgate")
                + " &8| &7PlaceholderAPI: &f" + Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI")));
        sender.sendMessage(Colors.legacy("&7EssentialsX: &f" + Bukkit.getPluginManager().isPluginEnabled("Essentials")
                + " &8| &7AxTrade: &f" + Bukkit.getPluginManager().isPluginEnabled("AxTrade")));
        sender.sendMessage(Colors.legacy("&7Reports: &f" + plugin.reports().enabled()
                + " &8| &7Open: &f" + plugin.reports().count(ReportService.Status.OPEN)
                + " &8| &7Resolved: &f" + plugin.reports().count(ReportService.Status.RESOLVED)));
        sender.sendMessage(Colors.legacy("&7Action limits: &f" + plugin.getConfig().getInt("menu.actions.max-actions-per-chain", 32)
                + " actions &8/ &f" + plugin.getConfig().getLong("menu.actions.max-total-delay-ticks", 1200L) + " ticks delay"));
    }

    private String shorten(String value, int max) {
        if (value == null) return "";
        return value.length() <= max ? value : value.substring(0, Math.max(0, max - 3)) + "...";
    }

    private void sendUsage(CommandSender sender, String label) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook &fv1.9.8 &8- &7Admin Tools"));
        sender.sendMessage(Colors.legacy("&f/" + label + " <give|remove|fix|refresh|status|tutorialreset|tutorialshow> <player>"));
        sender.sendMessage(Colors.legacy("&f/" + label + " menudebug <player> [menu] &8- &7cek alasan tombol tampil/hilang"));
        sender.sendMessage(Colors.legacy("&f/" + label + " reports [page] [open|resolved|all] &8- &7list report"));
        sender.sendMessage(Colors.legacy("&f/" + label + " reports <search|recent|player|category> ... &8- &7QoL report lookup"));
        sender.sendMessage(Colors.legacy("&f/" + label + " report <view|resolve|reopen|delete|note|audit> <id> [text]"));
        sender.sendMessage(Colors.legacy("&f/" + label + " health &8- &7cek dependency + production limits"));
    }

    @Override
    public @Nullable List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                                 @NotNull String alias, @NotNull String[] args) {
        if (!sender.hasPermission(PERMISSION)) return List.of();
        if (args.length == 1) {
            String p = args[0].toLowerCase(Locale.ROOT);
            return List.of("give","remove","fix","refresh","status","menudebug","tutorialreset","tutorialshow","reports","report","health")
                    .stream().filter(v -> v.startsWith(p)).toList();
        }
        if (args[0].equalsIgnoreCase("report")) {
            if (args.length == 2) return List.of("view","resolve","reopen","delete","note","audit").stream().filter(v -> v.startsWith(args[1].toLowerCase(Locale.ROOT))).toList();
            return List.of();
        }
        if (args[0].equalsIgnoreCase("reports")) {
            if (args.length == 2) return List.of("search","recent","player","category").stream().filter(v -> v.startsWith(args[1].toLowerCase(Locale.ROOT))).toList();
            if (args.length == 3 && args[1].equalsIgnoreCase("category")) return plugin.reports().categories().stream().filter(v -> v.toLowerCase(Locale.ROOT).startsWith(args[2].toLowerCase(Locale.ROOT))).toList();
            if (args.length == 4 && args[1].equalsIgnoreCase("category")) return List.of("open","resolved","all").stream().filter(v -> v.startsWith(args[3].toLowerCase(Locale.ROOT))).toList();
            if (args.length == 3 && !List.of("search","recent","player","category").contains(args[1].toLowerCase(Locale.ROOT))) return List.of("open","resolved","all").stream().filter(v -> v.startsWith(args[2].toLowerCase(Locale.ROOT))).toList();
            return List.of();
        }
        if (args.length == 2) {
            String p = args[1].toLowerCase(Locale.ROOT);
            return Bukkit.getOnlinePlayers().stream().map(Player::getName).filter(n -> n.toLowerCase(Locale.ROOT).startsWith(p)).sorted(String.CASE_INSENSITIVE_ORDER).toList();
        }
        if (args[0].equalsIgnoreCase("menudebug") && args.length == 3) {
            List<String> ids = new ArrayList<>(); ids.add("main");
            var sec = plugin.getConfig().getConfigurationSection("menu.submenus"); if (sec != null) ids.addAll(sec.getKeys(false));
            String p=args[2].toLowerCase(Locale.ROOT); return ids.stream().filter(v -> v.toLowerCase(Locale.ROOT).startsWith(p)).sorted().toList();
        }
        return List.of();
    }
}
