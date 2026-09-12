package id.cadera.memberbook.menu;

import id.cadera.memberbook.CdrMemberBookPlugin;
import org.bukkit.Sound;
import org.bukkit.entity.Player;

import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

public final class MenuActionService {
    private final CdrMemberBookPlugin plugin;
    private final Map<UUID, Long> generations = new HashMap<>();
    private final Map<UUID, Long> cooldownUntil = new HashMap<>();

    public MenuActionService(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    public boolean execute(Player player, List<MenuConfigService.MenuAction> actions) {
        if (actions == null || actions.isEmpty()) return false;
        if (!plugin.getConfig().getBoolean("menu.actions.enabled", true)) return false;

        int maxActions = Math.max(1, plugin.getConfig().getInt("menu.actions.max-actions-per-chain", 32));
        if (actions.size() > maxActions) {
            plugin.getLogger().warning("Blocked menu action chain for " + player.getName()
                    + ": " + actions.size() + " actions exceeds max " + maxActions + ".");
            plugin.message(player, "action-chain-invalid");
            return false;
        }

        long maxDelay = Math.max(0L, plugin.getConfig().getLong("menu.actions.max-total-delay-ticks", 1200L));
        long totalDelay = 0L;
        for (MenuConfigService.MenuAction action : actions) {
            if (!"delay".equalsIgnoreCase(action.type())) continue;
            long ticks = Math.max(1L, action.ticks());
            if (ticks > maxDelay || totalDelay > maxDelay - ticks) {
                plugin.getLogger().warning("Blocked menu action chain for " + player.getName()
                        + ": total delay exceeds " + maxDelay + " ticks.");
                plugin.message(player, "action-chain-invalid");
                return false;
            }
            totalDelay += ticks;
        }

        UUID uuid = player.getUniqueId();
        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(uuid, 0L);
        if (until > now) {
            plugin.message(player, "action-chain-cooldown");
            return false;
        }
        long cooldownTicks = Math.max(0L, plugin.getConfig().getLong("menu.actions.click-cooldown-ticks", 10L));
        if (cooldownTicks > 0L) cooldownUntil.put(uuid, now + cooldownTicks * 50L);

        // Starting a new chain supersedes delayed continuations from an older chain.
        long token = generations.getOrDefault(uuid, 0L) + 1L;
        generations.put(uuid, token);
        run(uuid, token, actions, 0);
        return true;
    }

    private void run(UUID uuid, long token, List<MenuConfigService.MenuAction> actions, int index) {
        if (!isCurrent(uuid, token) || index >= actions.size()) return;
        Player player = plugin.getServer().getPlayer(uuid);
        if (player == null || !player.isOnline()) {
            cancel(uuid);
            return;
        }

        MenuConfigService.MenuAction action = actions.get(index);
        String type = action.type() == null ? "" : action.type().toLowerCase(Locale.ROOT);
        if ("delay".equals(type)) {
            long ticks = Math.max(1L, action.ticks());
            plugin.getServer().getScheduler().runTaskLater(plugin,
                    () -> run(uuid, token, actions, index + 1), ticks);
            return;
        }

        boolean failed = false;
        try {
            switch (type) {
                case "command" -> plugin.dispatchActionCommand(player, action.value(), action.executor());
                case "console-command" -> plugin.dispatchActionCommand(player, action.value(), "console");
                case "message" -> player.sendMessage(plugin.formatMenuText(action.value(), player));
                case "sound" -> {
                    Sound sound = Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT));
                    player.playSound(player.getLocation(), sound, action.volume(), action.pitch());
                }
                case "close" -> player.closeInventory();
                case "open-menu" -> plugin.openMenu(player, action.value());
                default -> {
                    failed = true;
                    plugin.getLogger().warning("Unknown menu action type: " + action.type());
                }
            }
        } catch (Throwable throwable) {
            failed = true;
            plugin.getLogger().warning("Menu action failed for " + player.getName() + " [" + action.type()
                    + "]: " + throwable.getClass().getSimpleName() + ": " + throwable.getMessage());
        }

        if (failed && plugin.getConfig().getBoolean("menu.actions.stop-on-error", false)) {
            generations.remove(uuid);
            return;
        }
        run(uuid, token, actions, index + 1);
    }

    private boolean isCurrent(UUID uuid, long token) {
        return generations.getOrDefault(uuid, -1L) == token;
    }

    public void cancel(UUID uuid) {
        generations.remove(uuid);
        cooldownUntil.remove(uuid);
    }

    public void shutdown() {
        generations.clear();
        cooldownUntil.clear();
    }
}
