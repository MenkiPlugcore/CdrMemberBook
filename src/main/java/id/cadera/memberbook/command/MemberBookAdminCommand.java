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
    private static final String PERMISSION = "moonsignmenu.admin.memberbook";

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
            default -> sendUsage(sender, label);
        }
        return true;
    }

    private void sendUsage(CommandSender sender, String label) {
        sender.sendMessage(Colors.legacy("&dCdrMemberBook &fv1.4.0 &8- &7Admin Recovery"));
        sender.sendMessage(Colors.legacy("&f/" + label + " give <player> &8- &7pastikan player punya satu buku"));
        sender.sendMessage(Colors.legacy("&f/" + label + " remove <player> &8- &7hapus buku dan tahan recovery sampai relog"));
        sender.sendMessage(Colors.legacy("&f/" + label + " fix <player> &8- &7bersihkan duplicate + recovery"));
    }

    @Override
    public @Nullable List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                                 @NotNull String alias, @NotNull String[] args) {
        if (!sender.hasPermission(PERMISSION)) return List.of();

        if (args.length == 1) {
            String prefix = args[0].toLowerCase(Locale.ROOT);
            List<String> result = new ArrayList<>();
            for (String sub : List.of("give", "remove", "fix")) {
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
