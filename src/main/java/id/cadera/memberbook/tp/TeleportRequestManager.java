package id.cadera.memberbook.tp;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.scheduler.BukkitTask;
import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Sounds;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public final class TeleportRequestManager {
    private final CdrMemberBookPlugin plugin;
    private final ToggleStore toggleStore;
    private final Map<UUID, TeleportRequest> incomingByTarget = new HashMap<>();
    private final Map<UUID, Long> lastSent = new HashMap<>();
    private final Map<UUID, BukkitTask> expiryTasks = new HashMap<>();

    public TeleportRequestManager(CdrMemberBookPlugin plugin, ToggleStore toggleStore) {
        this.plugin = plugin;
        this.toggleStore = toggleStore;
    }

    public ToggleStore toggles() {
        return toggleStore;
    }

    public boolean create(Player requester, Player target, TeleportMode mode) {
        if (requester.getUniqueId().equals(target.getUniqueId())) {
            plugin.message(requester, "cannot-target-self");
            return false;
        }

        if (toggleStore.isDisabled(target.getUniqueId()) && !requester.hasPermission("cdrmemberbook.bypass.disabled")) {
            plugin.message(requester, "requests-disabled", "%player%", target.getName());
            return false;
        }

        if (plugin.getConfig().getBoolean("teleport.block-cross-world", false)
                && !requester.getWorld().equals(target.getWorld())) {
            plugin.message(requester, "cross-world-blocked");
            return false;
        }

        TeleportRequest existing = incomingByTarget.get(target.getUniqueId());
        if (existing != null) {
            plugin.message(requester, "target-has-request", "%player%", target.getName());
            return false;
        }

        if (!requester.hasPermission("cdrmemberbook.bypass.cooldown")) {
            int cooldown = Math.max(0, plugin.getConfig().getInt("teleport.request-cooldown-seconds", 5));
            long last = lastSent.getOrDefault(requester.getUniqueId(), 0L);
            long remainingMs = (last + cooldown * 1000L) - System.currentTimeMillis();
            if (remainingMs > 0) {
                long seconds = (remainingMs + 999L) / 1000L;
                plugin.message(requester, "cooldown", "%seconds%", String.valueOf(seconds));
                return false;
            }
        }

        TeleportRequest request = new TeleportRequest(
                requester.getUniqueId(), target.getUniqueId(), mode, System.currentTimeMillis());
        incomingByTarget.put(target.getUniqueId(), request);
        lastSent.put(requester.getUniqueId(), System.currentTimeMillis());

        if (mode == TeleportMode.TO_TARGET) {
            statusMessage(requester, "request-sent-to", "%player%", target.getName());
            plugin.message(target, "request-received-to", "%player%", requester.getName());
        } else {
            statusMessage(requester, "request-sent-here", "%player%", target.getName());
            plugin.message(target, "request-received-here", "%player%", requester.getName());
        }

        Sounds.play(plugin, target, "teleport.sounds.request");
        sendAcceptControls(target, requester, mode);
        scheduleExpiry(request);
        return true;
    }

    public boolean accept(Player target) {
        TeleportRequest request = incomingByTarget.remove(target.getUniqueId());
        cancelExpiry(target.getUniqueId());
        if (request == null) {
            plugin.message(target, "no-pending-request");
            return false;
        }

        Player requester = Bukkit.getPlayer(request.requesterId());
        if (requester == null || !requester.isOnline()) {
            plugin.message(target, "player-not-found");
            return false;
        }

        if (plugin.getConfig().getBoolean("teleport.block-cross-world", false)
                && !requester.getWorld().equals(target.getWorld())) {
            plugin.message(target, "cross-world-blocked");
            plugin.message(requester, "cross-world-blocked");
            return false;
        }

        statusMessage(target, "request-accepted");
        statusMessage(requester, "request-accepted");

        boolean success;
        Player moved;
        Player other;
        if (request.mode() == TeleportMode.TO_TARGET) {
            moved = requester;
            other = target;
            success = requester.teleport(target.getLocation());
        } else {
            moved = target;
            other = requester;
            success = target.teleport(requester.getLocation());
        }

        if (!success) {
            moved.sendMessage("§cTeleport gagal.");
            return false;
        }
        plugin.message(moved, "teleported");
        Sounds.play(plugin, moved, "teleport.sounds.accepted");
        Sounds.play(plugin, other, "teleport.sounds.accepted");
        return true;
    }

    public boolean deny(Player target) {
        TeleportRequest request = incomingByTarget.remove(target.getUniqueId());
        cancelExpiry(target.getUniqueId());
        if (request == null) {
            plugin.message(target, "no-pending-request");
            return false;
        }

        statusMessage(target, "request-denied");
        Sounds.play(plugin, target, "teleport.sounds.denied");
        Player requester = Bukkit.getPlayer(request.requesterId());
        if (requester != null) {
            statusMessage(requester, "target-denied", "%player%", target.getName());
            Sounds.play(plugin, requester, "teleport.sounds.denied");
        }
        return true;
    }

    public void removeRequestsFor(UUID uuid) {
        TeleportRequest ownIncoming = incomingByTarget.remove(uuid);
        if (ownIncoming != null) cancelExpiry(uuid);

        UUID targetToRemove = null;
        for (Map.Entry<UUID, TeleportRequest> entry : incomingByTarget.entrySet()) {
            if (entry.getValue().requesterId().equals(uuid)) {
                targetToRemove = entry.getKey();
                break;
            }
        }
        if (targetToRemove != null) {
            incomingByTarget.remove(targetToRemove);
            cancelExpiry(targetToRemove);
        }
    }

    public void handleWorldChange(Player player) {
        if (plugin.getConfig().getBoolean("teleport.cancel-on-world-change", true)) {
            removeRequestsFor(player.getUniqueId());
        }
    }

    private void statusMessage(Player player, String key, String... replacements) {
        if (plugin.preferences() != null && !plugin.preferences().tpStatusNotificationsEnabled(player)) return;
        plugin.message(player, key, replacements);
    }

    private void sendAcceptControls(Player target, Player requester, TeleportMode mode) {
        if (plugin.forms() != null && plugin.forms().isBedrock(target)) {
            plugin.forms().showIncomingRequest(target, requester, mode);
            return;
        }

        target.sendMessage("§a[TERIMA] §fketik §a/tpaccept   §c[TOLAK] §fketik §c/tpdeny");
    }

    private void scheduleExpiry(TeleportRequest request) {
        int seconds = Math.max(5, plugin.getConfig().getInt("teleport.request-expire-seconds", 30));
        BukkitTask task = Bukkit.getScheduler().runTaskLater(plugin, () -> {
            TeleportRequest current = incomingByTarget.get(request.targetId());
            if (current == null || !current.equals(request)) return;
            incomingByTarget.remove(request.targetId());
            expiryTasks.remove(request.targetId());

            Player requester = Bukkit.getPlayer(request.requesterId());
            Player target = Bukkit.getPlayer(request.targetId());
            if (requester != null) {
                statusMessage(requester, "request-expired-sender", "%player%", target == null ? "player" : target.getName());
            }
            if (target != null) {
                statusMessage(target, "request-expired-target", "%player%", requester == null ? "player" : requester.getName());
            }
        }, seconds * 20L);
        expiryTasks.put(request.targetId(), task);
    }

    private void cancelExpiry(UUID targetId) {
        BukkitTask task = expiryTasks.remove(targetId);
        if (task != null) task.cancel();
    }
}
