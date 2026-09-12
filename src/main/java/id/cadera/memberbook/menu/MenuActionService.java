package id.cadera.memberbook.menu;

import id.cadera.memberbook.CdrMemberBookPlugin;
import org.bukkit.Sound;
import org.bukkit.entity.Player;

import java.util.List;
import java.util.Locale;

public final class MenuActionService {
    private final CdrMemberBookPlugin plugin;
    public MenuActionService(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    public void execute(Player player, List<MenuConfigService.MenuAction> actions) {
        if (actions == null || actions.isEmpty()) return;
        run(player, actions, 0);
    }

    private void run(Player player, List<MenuConfigService.MenuAction> actions, int index) {
        if (!player.isOnline() || index >= actions.size()) return;
        MenuConfigService.MenuAction action = actions.get(index);
        String type = action.type().toLowerCase(Locale.ROOT);
        try {
            switch (type) {
                case "delay" -> {
                    long ticks = Math.max(1L, action.ticks());
                    plugin.getServer().getScheduler().runTaskLater(plugin, () -> run(player, actions, index + 1), ticks);
                    return;
                }
                case "command" -> plugin.dispatchActionCommand(player, action.value(), action.executor());
                case "console-command" -> plugin.dispatchActionCommand(player, action.value(), "console");
                case "message" -> player.sendMessage(plugin.formatMenuText(action.value(), player));
                case "sound" -> {
                    Sound sound = Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT));
                    player.playSound(player.getLocation(), sound, action.volume(), action.pitch());
                }
                case "close" -> player.closeInventory();
                case "open-menu" -> plugin.openMenu(player, action.value());
                default -> plugin.getLogger().warning("Unknown menu action type: " + action.type());
            }
        } catch (Throwable throwable) {
            plugin.getLogger().warning("Menu action failed [" + action.type() + "]: " + throwable.getMessage());
        }
        run(player, actions, index + 1);
    }
}
