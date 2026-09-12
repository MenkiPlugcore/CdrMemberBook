package id.cadera.memberbook.command;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.item.MemberBookService;
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

    public MemberBookAdminCommand(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (!sender.hasPermission(PERMISSION)) {
            sender.sendMessage(Colors.legacy("&cKamu tidak punya izin untuk command ini."));
            return true;
        }

        if (args.length < 2) {
            sendUsage(sender, label);
            return true;
        }

        Player target = Bukkit.getPlayerExact(args[1]);
        if (target == null) {
            sender.sendMessage(Colors.legacy("&cPlayer &f" + args[1] + " &ctidak ditemukan atau sedang offline."));
            return true;
        }

        MemberBookService service = plugin.memberBook();
        String action = args[0].toLowerCase(Locale.ROOT);

        switch (action) {
            case "give" -> {
                if (!service.isEligibleForBook(target)) {
                    sender.sendMessage(Colors.legacy("&e" + target.getName()
                            + " &cbukan player yang eligible menerima Member Book (default: Bedrock/Floodgate only)."));
                    return true;
                }
                boolean success = service.forceGive(target);
                if (success) {
                    sender.sendMessage(Colors.legacy("&aMember Book dipastikan tersedia untuk &f" + target.getName() + "&a."));
                } else {
                    sender.sendMessage(Colors.legacy("&eInventory/cursor &f" + target.getName()
                            + " &epenuh. Kosongkan satu slot lalu ulangi command."));
                }
            }
            case "remove" -> {
                int removed = service.forceRemove(target);
                sender.sendMessage(Colors.legacy("&aMenghapus &f" + removed + " &acopy Member Book dari &f"
                        + target.getName() + "&a. Auto-recovery ditahan sampai player login ulang atau di-fix/give."));
            }
            case "fix" -> {
                if (!service.isEligibleForBook(target)) {
                    sender.sendMessage(Colors.legacy("&e" + target.getName()
                            + " &cbukan player yang eligible menerima Member Book (default: Bedrock/Floodgate only)."));
                    return true;
                }
                boolean success = service.forceRepair(target);
                if (success) {
                    sender.sendMessage(Colors.legacy("&aMember Book &f" + target.getName()
                            + " &aberhasil diperiksa: duplicate dibersihkan dan recovery dijalankan."));
                } else {
                    sender.sendMessage(Colors.legacy("&eRecovery belum bisa menaruh buku ke inventory/cursor &f"
                            + target.getName() + "&e karena penuh."));
                }
            }
            case "refresh" -> {
                if (!service.isEligibleForBook(target)) {
                    sender.sendMessage(Colors.legacy("&e" + target.getName()
                            + " &cbukan player yang eligible menerima Member Book (default: Bedrock/Floodgate only)."));
                    return true;
                }
                boolean success = service.refreshDynamicBook(target);
                if (success) {
                    sender.sendMessage(Colors.legacy("&aDynamic Member Book &f" + target.getName()
                            + " &aberhasil direfresh."));
                } else {
                    sender.sendMessage(Colors.legacy("&eTidak ada Member Book aktif yang bisa direfresh untuk &f"
                            + target.getName() + "&e."));
                }
            }
            case "menudebug" -> {
                String menuId = args.length >= 3 ? args[2] : "main";
                var menu = plugin.menus().getMenu(menuId);
                if (menu == null) { sender.sendMessage(Colors.legacy("&cMenu tidak ditemukan: &f" + menuId)); break; }
                boolean hidePerm = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
                boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);
                sender.sendMessage(Colors.legacy("&dMenu Debug &8- &f" + target.getName() + " &8/ &f" + menu.id()));
                for (var button : menu.buttons()) {
                    boolean permission = plugin.menus().canUse(target, button);
                    var available = plugin.menus().availability(target, button);
                    boolean visible = (!hidePerm || permission) && (!hideUnavailable || available.available());
                    sender.sendMessage(Colors.legacy((visible ? "&a✔ " : "&c✘ ") + "&f" + button.key() + " &8| &7type=&f" + button.type()
                            + " &8| &7perm=&f" + permission + " &8| &7availability=&f" + available.code()
                            + (available.detail().isBlank() ? "" : " &8(" + available.detail() + ")")));
                }
            }
            case "status" -> {
                MemberBookService.BookStatus status = service.inspect(target);
                sender.sendMessage(Colors.legacy("&dCdrMemberBook Status &8- &f" + target.getName()));
                sender.sendMessage(Colors.legacy("&7Mode: &f" + status.mode()
                        + (status.configuredModeValid() ? "" : " &c(config invalid -> fallback)")));
                sender.sendMessage(Colors.legacy("&7Platform: &f" + (status.bedrock() ? "Bedrock" : "Java")
                        + " &8| &7Eligible: &f" + status.eligible()));
                sender.sendMessage(Colors.legacy("&7Copies: &f" + status.visibleCopies()
                        + " &8(inv=" + status.inventoryCopies() + ", cursor=" + status.cursorBook()
                        + ", external=" + status.externalCopies() + ")"));
                sender.sendMessage(Colors.legacy("&7Reserved slot: &f" + status.reservedSlot()
                        + " &8| &7Book in slot: &f" + status.bookInReservedSlot()));
                sender.sendMessage(Colors.legacy("&7Recovery: &f" + status.recoveryEnabled()
                        + " &8| &7Suppressed: &f" + status.recoverySuppressed()
                        + " &8| &7Fixed return pending: &f" + status.fixedReturnPending()));
                sender.sendMessage(Colors.legacy("&7External protection: &f" + status.externalStorageProtected()
                        + " &8| &7Drop protection: &f" + status.dropProtected()
                        + " &8| &7Dynamic: &f" + status.dynamicEnabled()));
            }
            case "tutorialreset" -> {
                plugin.tutorial().reset(target);
                sender.sendMessage(Colors.legacy("&aFirst Join Tutorial di-reset untuk &f" + target.getName()
                        + "&a. Tutorial akan tersedia lagi pada join berikutnya."));
            }
            case "tutorialshow" -> {
                if (!plugin.tutorial().canShow(target)) {
                    sender.sendMessage(Colors.legacy("&eTutorial native hanya bisa ditampilkan ke player Bedrock/Floodgate yang online saat fitur aktif."));
                    return true;
                }
                plugin.tutorial().showNow(target);
                sender.sendMessage(Colors.legacy("&aFirst Join Tutorial ditampilkan ke &f" + target.getName() + "&a."));
            }
            default -> sendUsage(sender, label);
        }
        return true;
    }

    private void sendUsage(CommandSender sender, String label) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook &fv1.8.3 &8- &7Admin Tools"));
        sender.sendMessage(Colors.legacy("&f/" + label + " give <player> &8- &7pastikan player punya satu buku"));
        sender.sendMessage(Colors.legacy("&f/" + label + " remove <player> &8- &7hapus buku dan tahan recovery sampai relog"));
        sender.sendMessage(Colors.legacy("&f/" + label + " fix <player> &8- &7bersihkan duplicate + recovery"));
        sender.sendMessage(Colors.legacy("&f/" + label + " refresh <player> &8- &7refresh placeholder nama/lore"));
        sender.sendMessage(Colors.legacy("&f/" + label + " status <player> &8- &7diagnostic Book Modes + recovery"));
        sender.sendMessage(Colors.legacy("&f/" + label + " menudebug <player> [menu] &8- &7cek tombol tampil/hilang"));
        sender.sendMessage(Colors.legacy("&f/" + label + " tutorialreset <player> &8- &7reset tutorial player"));
        sender.sendMessage(Colors.legacy("&f/" + label + " tutorialshow <player> &8- &7paksa tampilkan tutorial Bedrock"));
    }

    @Override
    public @Nullable List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                                 @NotNull String alias, @NotNull String[] args) {
        if (!sender.hasPermission(PERMISSION)) return List.of();

        if (args.length == 1) {
            String prefix = args[0].toLowerCase(Locale.ROOT);
            List<String> result = new ArrayList<>();
            for (String sub : List.of("give", "remove", "fix", "refresh", "status", "menudebug", "tutorialreset", "tutorialshow")) {
                if (sub.startsWith(prefix)) result.add(sub);
            }
            return result;
        }

        if (args.length == 2) {
            String prefix = args[1].toLowerCase(Locale.ROOT);
            return Bukkit.getOnlinePlayers().stream()
                    .map(Player::getName)
                    .filter(name -> name.toLowerCase(Locale.ROOT).startsWith(prefix))
                    .sorted(String.CASE_INSENSITIVE_ORDER)
                    .toList();
        }

        return List.of();
    }
}
