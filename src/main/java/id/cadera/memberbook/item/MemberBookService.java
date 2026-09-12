package id.cadera.memberbook.item;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Colors;
import me.clip.placeholderapi.PlaceholderAPI;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.block.BlockDispenseEvent;
import org.bukkit.event.entity.EntityPickupItemEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.inventory.ClickType;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryCloseEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.event.inventory.InventoryMoveItemEvent;
import org.bukkit.event.inventory.InventoryOpenEvent;
import org.bukkit.event.inventory.InventoryPickupItemEvent;
import org.bukkit.event.inventory.InventoryType;
import org.bukkit.event.player.PlayerChangedWorldEvent;
import org.bukkit.event.player.PlayerDropItemEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerRespawnEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.scheduler.BukkitTask;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

public final class MemberBookService implements Listener {
    private static final int STORAGE_END = 35;

    private final CdrMemberBookPlugin plugin;
    private final NamespacedKey bookKey;
    private final Set<UUID> recoverySuppressed = new HashSet<>();
    private final Set<UUID> menuOpenCooldown = new HashSet<>();
    private final Set<UUID> fixedSlotReturnPending = new HashSet<>();
    private BukkitTask enforcementTask;
    private BukkitTask dynamicRefreshTask;

    public MemberBookService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.bookKey = new NamespacedKey(plugin, "member-book");
    }

    public void startEnforcement() {
        stopEnforcement();
        if (!isEnabled()) return;

        BookMode mode = bookMode();
        boolean needsEnforcement = mode == BookMode.LOCKED_HOTBAR
                || mode == BookMode.FIXED_SLOT_MOVABLE
                || (mode == BookMode.MOVABLE && recoveryEnabled());

        if (needsEnforcement) {
            long configuredPeriod = switch (mode) {
                case LOCKED_HOTBAR -> plugin.getConfig().getLong("member-book.enforce-interval-ticks", 20L);
                case FIXED_SLOT_MOVABLE -> plugin.getConfig().getLong(
                        "member-book.fixed-slot.return-delay-ticks", 40L);
                default -> plugin.getConfig().getLong("member-book.recovery.interval-ticks", 100L);
            };
            long period = Math.max(20L, configuredPeriod);

            enforcementTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
                for (Player player : Bukkit.getOnlinePlayers()) {
                    syncBookState(player, false);
                }
            }, period, period);
        }

        startDynamicRefresh();
    }

    private void startDynamicRefresh() {
        if (!dynamicEnabled()) return;
        long period = Math.max(40L, plugin.getConfig().getLong(
                "member-book.dynamic.refresh-interval-ticks", 200L));
        dynamicRefreshTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
            for (Player player : Bukkit.getOnlinePlayers()) {
                refreshDynamicBook(player);
            }
        }, period, period);
    }

    public void restartEnforcement() {
        startEnforcement();
    }

    public void stopEnforcement() {
        if (enforcementTask != null) {
            enforcementTask.cancel();
            enforcementTask = null;
        }
        if (dynamicRefreshTask != null) {
            dynamicRefreshTask.cancel();
            dynamicRefreshTask = null;
        }
    }

    public void giveToOnlinePlayers() {
        if (!isEnabled()) return;
        for (Player player : Bukkit.getOnlinePlayers()) {
            if (isEligibleForBook(player) && refreshExistingEnabled()) {
                refreshVisibleBookAppearance(player);
            }
            syncBookState(player, false);
        }
    }

    public void refreshOnlineBooks() {
        if (!isEnabled() || !refreshExistingEnabled()) return;
        for (Player player : Bukkit.getOnlinePlayers()) {
            if (isEligibleForBook(player)) refreshVisibleBookAppearance(player);
        }
    }

    public void ensureBook(Player player) {
        if (!isEligibleForBook(player) || recoverySuppressed.contains(player.getUniqueId())) return;
        syncBookState(player, true);
    }

    public boolean isMemberBook(ItemStack item) {
        if (item == null || item.getType().isAir() || !item.hasItemMeta()) return false;
        Byte marker = item.getItemMeta().getPersistentDataContainer().get(bookKey, PersistentDataType.BYTE);
        return marker != null && marker == (byte) 1;
    }

    public boolean isEligibleForBook(Player player) {
        if (!isEnabled()) return false;
        if (!isBedrockOnly()) return true;
        return plugin.forms() != null && plugin.forms().isBedrock(player);
    }

    public boolean forceGive(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        if (refreshExistingEnabled()) refreshVisibleBookAppearance(player);
        boolean given = reconcileMovableBook(player, true, true, true);
        return given && finishBookMode(player);
    }

    public boolean forceRepair(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        if (refreshExistingEnabled()) refreshVisibleBookAppearance(player);
        boolean repaired = reconcileMovableBook(player, true, true, true);
        if (!repaired) return false;
        return finishBookMode(player);
    }

    public int forceRemove(Player player) {
        recoverySuppressed.add(player.getUniqueId());
        return removeAllVisibleBooks(player, true);
    }

    private boolean finishBookMode(Player player) {
        BookMode mode = bookMode();
        if (mode != BookMode.LOCKED_HOTBAR && mode != BookMode.FIXED_SLOT_MOVABLE) {
            return hasOwnedBook(player);
        }
        if (isMemberBook(player.getItemOnCursor())) return true;
        ensureLockedHotbarBook(player);
        return hasOwnedBook(player);
    }

    private void syncBookState(Player player, boolean notifyFull) {
        if (!isEnabled()) return;

        if (!isEligibleForBook(player)) {
            if (isBedrockOnly()) removeAllVisibleBooks(player, false);
            return;
        }

        if (recoverySuppressed.contains(player.getUniqueId())) return;

        BookMode mode = bookMode();
        if (mode == BookMode.NORMAL) {
            // NORMAL behaves like a regular item: no periodic recovery, slot enforcement,
            // duplicate cleanup, drop protection or external-storage protection.
            if (notifyFull && giveOnJoinEnabled() && !hasOwnedBook(player)) {
                if (!placeBookInPlayer(player, createBook(player))) {
                    plugin.message(player, "member-book-inventory-full");
                }
            }
            return;
        }

        if (mode == BookMode.LOCKED_HOTBAR || mode == BookMode.FIXED_SLOT_MOVABLE) {
            reconcileMovableBook(player, false, false, false);
            if (isMemberBook(player.getItemOnCursor())) return;
            ensureLockedHotbarBook(player);
            return;
        }

        reconcileMovableBook(player, shouldMaintain(), notifyFull, false);
    }

    private boolean reconcileMovableBook(Player player, boolean allowCreate,
                                         boolean notifyFull, boolean forceDuplicateCleanup) {
        PlayerInventory inventory = player.getInventory();
        boolean cleanupDuplicates = forceDuplicateCleanup || removeDuplicatesEnabled();

        int keepSlot = -1;
        for (int slot = 0; slot < inventory.getSize(); slot++) {
            ItemStack item = inventory.getItem(slot);
            if (!isMemberBook(item)) continue;

            if (keepSlot < 0) {
                keepSlot = slot;
            } else if (cleanupDuplicates) {
                inventory.setItem(slot, null);
            }
        }

        boolean inventoryBook = keepSlot >= 0;
        boolean cursorBook = isMemberBook(player.getItemOnCursor());

        if (inventoryBook && cursorBook && cleanupDuplicates) {
            player.setItemOnCursor(null);
            cursorBook = false;
        }

        boolean hasOwned = inventoryBook || cursorBook;

        if (recoverFromOpenContainer() && isExternalView(player)) {
            hasOwned = recoverExternalBooks(player, player.getOpenInventory().getTopInventory(), hasOwned,
                    cleanupDuplicates, notifyFull);
        }

        if (!hasOwned && allowCreate) {
            hasOwned = placeBookInPlayer(player, createBook(player));
            if (!hasOwned && notifyFull) plugin.message(player, "member-book-inventory-full");
        }

        return hasOwned;
    }

    private boolean recoverExternalBooks(Player player, Inventory inventory, boolean alreadyOwned,
                                         boolean cleanupDuplicates, boolean notifyFull) {
        List<Integer> externalBookSlots = new ArrayList<>();
        for (int slot = 0; slot < inventory.getSize(); slot++) {
            if (isMemberBook(inventory.getItem(slot))) externalBookSlots.add(slot);
        }

        if (externalBookSlots.isEmpty()) return alreadyOwned;

        if (alreadyOwned) {
            for (int slot : externalBookSlots) inventory.setItem(slot, null);
            return true;
        }

        int firstSlot = externalBookSlots.getFirst();
        ItemStack recovered = inventory.getItem(firstSlot);
        if (recovered == null || recovered.getType().isAir()) return false;

        if (!placeBookInPlayer(player, recovered.clone())) {
            if (notifyFull) plugin.message(player, "member-book-inventory-full");
            return false;
        }

        inventory.setItem(firstSlot, null);
        if (cleanupDuplicates || externalBookSlots.size() > 1) {
            for (int i = 1; i < externalBookSlots.size(); i++) {
                inventory.setItem(externalBookSlots.get(i), null);
            }
        }
        return true;
    }

    private boolean placeBookInPlayer(Player player, ItemStack book) {
        PlayerInventory inventory = player.getInventory();
        int slot = reservedSlot();
        ItemStack current = inventory.getItem(slot);

        if (current == null || current.getType().isAir()) {
            inventory.setItem(slot, book);
            return true;
        }

        if (inventory.addItem(book).isEmpty()) return true;

        ItemStack cursor = player.getItemOnCursor();
        if (cursor == null || cursor.getType().isAir()) {
            player.setItemOnCursor(book);
            return true;
        }

        return false;
    }

    private void ensureLockedHotbarBook(Player player) {
        PlayerInventory inventory = player.getInventory();
        int slot = reservedSlot();
        ItemStack current = inventory.getItem(slot);

        if (isMemberBook(current)) {
            removeDuplicateBooks(inventory, slot);
            return;
        }

        int sourceSlot = findStorageBookSlot(inventory, slot);
        ItemStack book = sourceSlot >= 0 ? inventory.getItem(sourceSlot) : createBook(player);
        if (book == null) book = createBook(player);

        if (current != null && !current.getType().isAir()) {
            if (sourceSlot >= 0) {
                inventory.setItem(sourceSlot, current);
            } else {
                int freeSlot = findFreeStorageSlot(inventory, slot);
                if (freeSlot < 0) return;
                inventory.setItem(freeSlot, current);
            }
        } else if (sourceSlot >= 0) {
            inventory.setItem(sourceSlot, null);
        }

        inventory.setItem(slot, book);
        removeDuplicateBooks(inventory, slot);
    }

    private int findStorageBookSlot(PlayerInventory inventory, int excludedSlot) {
        for (int slot = 0; slot <= STORAGE_END; slot++) {
            if (slot == excludedSlot) continue;
            if (isMemberBook(inventory.getItem(slot))) return slot;
        }
        return -1;
    }

    private int findFreeStorageSlot(PlayerInventory inventory, int excludedSlot) {
        for (int slot = 9; slot <= STORAGE_END; slot++) {
            if (slot == excludedSlot) continue;
            ItemStack item = inventory.getItem(slot);
            if (item == null || item.getType().isAir()) return slot;
        }
        for (int slot = 0; slot <= 8; slot++) {
            if (slot == excludedSlot) continue;
            ItemStack item = inventory.getItem(slot);
            if (item == null || item.getType().isAir()) return slot;
        }
        return -1;
    }

    private void removeDuplicateBooks(PlayerInventory inventory, int keepSlot) {
        for (int slot = 0; slot < inventory.getSize(); slot++) {
            if (slot == keepSlot) continue;
            if (isMemberBook(inventory.getItem(slot))) inventory.setItem(slot, null);
        }
    }

    private int removeAllVisibleBooks(Player player, boolean includeOpenTop) {
        int removed = 0;
        PlayerInventory inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getSize(); slot++) {
            if (isMemberBook(inventory.getItem(slot))) {
                inventory.setItem(slot, null);
                removed++;
            }
        }

        if (isMemberBook(player.getItemOnCursor())) {
            player.setItemOnCursor(null);
            removed++;
        }

        if (includeOpenTop && isExternalView(player)) {
            Inventory top = player.getOpenInventory().getTopInventory();
            for (int slot = 0; slot < top.getSize(); slot++) {
                if (isMemberBook(top.getItem(slot))) {
                    top.setItem(slot, null);
                    removed++;
                }
            }
        }

        return removed;
    }

    private boolean hasOwnedBook(Player player) {
        for (ItemStack item : player.getInventory().getContents()) {
            if (isMemberBook(item)) return true;
        }
        return isMemberBook(player.getItemOnCursor());
    }

    private ItemStack createBook(Player player) {
        String materialName = plugin.getConfig().getString("member-book.material", "BOOK");
        Material material = materialName == null ? Material.BOOK : Material.matchMaterial(materialName);
        if (material == null) material = Material.BOOK;

        ItemStack item = new ItemStack(material);
        applyConfiguredAppearance(item, player);
        return item;
    }

    private void applyConfiguredAppearance(ItemStack item, Player player) {
        ItemMeta meta = item.getItemMeta();
        if (meta == null) return;

        String configuredName = plugin.getConfig().getString(
                "member-book.name", "&d&lMOONSIGN &fMember Book");
        meta.setDisplayName(Colors.legacy(renderDynamicText(player, configuredName)));

        List<String> lore = new ArrayList<>();
        for (String line : plugin.getConfig().getStringList("member-book.lore")) {
            lore.add(Colors.legacy(renderDynamicText(player, line)));
        }
        meta.setLore(lore.isEmpty() ? null : lore);

        String base = "member-book.customization.";

        int customModelData = plugin.getConfig().getInt(base + "custom-model-data", 0);
        if (customModelData > 0) meta.setCustomModelData(customModelData);

        String itemModelName = plugin.getConfig().getString(base + "item-model", "");
        if (itemModelName != null && !itemModelName.isBlank()) {
            NamespacedKey itemModel = NamespacedKey.fromString(itemModelName.trim());
            if (itemModel != null) meta.setItemModel(itemModel);
        }

        String glintMode = plugin.getConfig().getString(base + "enchant-glint", "default");
        if (glintMode != null) {
            switch (glintMode.trim().toLowerCase()) {
                case "true", "on", "yes", "enabled" -> meta.setEnchantmentGlintOverride(true);
                case "false", "off", "no", "disabled" -> meta.setEnchantmentGlintOverride(false);
                default -> meta.setEnchantmentGlintOverride(null);
            }
        }

        meta.setHideTooltip(plugin.getConfig().getBoolean(base + "hide-tooltip", false));
        if (plugin.getConfig().getBoolean(base + "hide-attributes", false)) {
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES);
        }
        if (plugin.getConfig().getBoolean(base + "hide-additional-tooltip", false)) {
            meta.addItemFlags(ItemFlag.HIDE_ADDITIONAL_TOOLTIP);
        }

        for (String configuredFlag : plugin.getConfig().getStringList(base + "item-flags")) {
            if (configuredFlag == null || configuredFlag.isBlank()) continue;
            try {
                meta.addItemFlags(ItemFlag.valueOf(configuredFlag.trim().toUpperCase()));
            } catch (IllegalArgumentException ignored) {
                // Invalid flags are ignored so a typo cannot prevent the plugin from starting.
            }
        }

        meta.getPersistentDataContainer().set(bookKey, PersistentDataType.BYTE, (byte) 1);
        item.setItemMeta(meta);
    }

    public void refreshVisibleBookAppearance(Player player) {
        PlayerInventory inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getSize(); slot++) {
            ItemStack current = inventory.getItem(slot);
            if (isMemberBook(current)) inventory.setItem(slot, refreshedBook(player));
        }

        ItemStack cursor = player.getItemOnCursor();
        if (isMemberBook(cursor)) player.setItemOnCursor(refreshedBook(player));

        if (isExternalView(player)) {
            Inventory top = player.getOpenInventory().getTopInventory();
            for (int slot = 0; slot < top.getSize(); slot++) {
                ItemStack current = top.getItem(slot);
                if (isMemberBook(current)) top.setItem(slot, refreshedBook(player));
            }
        }
    }

    private ItemStack refreshedBook(Player player) {
        ItemStack refreshed = createBook(player);
        refreshed.setAmount(1);
        return refreshed;
    }

    public boolean refreshDynamicBook(Player player) {
        if (!dynamicEnabled() || !isEligibleForBook(player)
                || recoverySuppressed.contains(player.getUniqueId()) || !hasOwnedBook(player)) {
            return false;
        }
        refreshVisibleBookAppearance(player);
        return true;
    }

    private String renderDynamicText(Player player, String value) {
        if (value == null || value.isEmpty()) return "";
        String rendered = value;

        if (plugin.getConfig().getBoolean("member-book.dynamic.built-in-placeholders", true)) {
            rendered = rendered
                    .replace("%player%", player.getName())
                    .replace("%uuid%", player.getUniqueId().toString())
                    .replace("%world%", player.getWorld().getName())
                    .replace("%ping%", Integer.toString(player.getPing()))
                    .replace("%online%", Integer.toString(Bukkit.getOnlinePlayers().size()));
        }

        if (placeholderApiEnabled()
                && plugin.getConfig().getBoolean("member-book.dynamic.placeholderapi", true)) {
            try {
                rendered = PlaceholderAPI.setPlaceholders(player, rendered);
            } catch (Throwable ignored) {
                // Keep built-in/original text if PlaceholderAPI or an expansion fails.
            }
        }
        return rendered;
    }

    private boolean placeholderApiEnabled() {
        return Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI");
    }

    private boolean dynamicEnabled() {
        return plugin.getConfig().getBoolean("member-book.dynamic.enabled", true);
    }

    private boolean refreshExistingEnabled() {
        return plugin.getConfig().getBoolean("member-book.customization.refresh-existing", true);
    }

    private boolean isEnabled() {
        return plugin.getConfig().getBoolean("member-book.enabled", true);
    }

    private boolean isBedrockOnly() {
        return plugin.getConfig().getBoolean("member-book.bedrock-only", true);
    }

    private boolean shouldMaintain() {
        return bookMode() != BookMode.NORMAL && giveOnJoinEnabled();
    }

    private boolean giveOnJoinEnabled() {
        return plugin.getConfig().getBoolean("member-book.give-on-join", true);
    }

    private BookMode bookMode() {
        String configured = plugin.getConfig().getString("member-book.mode", "");
        if (configured == null || configured.isBlank()) {
            return plugin.getConfig().getBoolean("member-book.permanent-hotbar", false)
                    ? BookMode.LOCKED_HOTBAR
                    : BookMode.MOVABLE;
        }
        try {
            return BookMode.valueOf(configured.trim().toUpperCase());
        } catch (IllegalArgumentException ignored) {
            return BookMode.MOVABLE;
        }
    }

    public String modeName() {
        return bookMode().name();
    }

    private boolean isPermanentHotbar() {
        return bookMode() == BookMode.LOCKED_HOTBAR;
    }

    private boolean preventExternalStorage() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.prevent-external-storage", true);
    }

    private boolean recoveryEnabled() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.enabled", true);
    }

    private boolean recoverFromOpenContainer() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.recover-from-open-container", true);
    }

    private boolean removeDuplicatesEnabled() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.remove-duplicates", true);
    }

    private boolean recoverOnWorldChange() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.recover-on-world-change", true);
    }

    private int reservedSlot() {
        int configuredSlot = plugin.getConfig().getInt("member-book.hotbar-slot", 8);
        return Math.max(0, Math.min(8, configuredSlot));
    }

    private boolean hasExternalTopInventory(InventoryClickEvent event) {
        InventoryType type = event.getView().getTopInventory().getType();
        return type != InventoryType.CRAFTING && type != InventoryType.CREATIVE;
    }

    private boolean isExternalView(Player player) {
        InventoryType type = player.getOpenInventory().getTopInventory().getType();
        return type != InventoryType.CRAFTING && type != InventoryType.CREATIVE;
    }

    private void denyExternalStorage(Player player) {
        plugin.message(player, "member-book-external-storage-blocked");
    }

    private void scheduleRepair(Player player) {
        if (bookMode() == BookMode.NORMAL) return;
        if (bookMode() == BookMode.FIXED_SLOT_MOVABLE) {
            UUID uuid = player.getUniqueId();
            if (!fixedSlotReturnPending.add(uuid)) return;
            long delay = Math.max(1L, plugin.getConfig().getLong(
                    "member-book.fixed-slot.return-delay-ticks", 40L));
            Bukkit.getScheduler().runTaskLater(plugin, () -> {
                fixedSlotReturnPending.remove(uuid);
                if (player.isOnline()) syncBookState(player, false);
            }, delay);
            return;
        }
        Bukkit.getScheduler().runTask(plugin, () -> {
            if (player.isOnline()) syncBookState(player, false);
        });
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        if (!isEnabled()) return;
        Player player = event.getPlayer();
        recoverySuppressed.remove(player.getUniqueId());
        long delay = Math.max(1L, plugin.getConfig().getLong("member-book.give-delay-ticks", 10L));
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            if (isEligibleForBook(player) && (refreshExistingEnabled()
                    || plugin.getConfig().getBoolean("member-book.dynamic.refresh-on-join", true))) {
                refreshVisibleBookAppearance(player);
            }
            syncBookState(player, true);
        }, delay);
    }

    @EventHandler
    public void onRespawn(PlayerRespawnEvent event) {
        if (!isEnabled()) return;
        Player player = event.getPlayer();
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) syncBookState(player, bookMode() != BookMode.NORMAL);
        }, 1L);
    }

    @EventHandler
    public void onWorldChange(PlayerChangedWorldEvent event) {
        if (!recoverOnWorldChange()) return;
        Player player = event.getPlayer();
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            if (dynamicEnabled() && plugin.getConfig().getBoolean(
                    "member-book.dynamic.refresh-on-world-change", true)) {
                refreshDynamicBook(player);
            }
            syncBookState(player, false);
        }, 1L);
    }

    @EventHandler
    public void onInteract(PlayerInteractEvent event) {
        Player player = event.getPlayer();
        if (!isEligibleForBook(player)) return;
        Action action = event.getAction();
        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;
        if (!isMemberBook(event.getItem())) return;

        event.setCancelled(true);
        UUID uuid = player.getUniqueId();
        long cooldownTicks = Math.max(0L, plugin.getConfig().getLong("member-book.open-cooldown-ticks", 20L));
        if (cooldownTicks > 0L) {
            if (!menuOpenCooldown.add(uuid)) return;
            Bukkit.getScheduler().runTaskLater(plugin, () -> menuOpenCooldown.remove(uuid), cooldownTicks);
        }
        plugin.openMenu(player);
    }

    @EventHandler
    public void onInventoryOpen(InventoryOpenEvent event) {
        if (!(event.getPlayer() instanceof Player player)) return;
        if (!isEligibleForBook(player) || !recoverFromOpenContainer()) return;
        scheduleRepair(player);
    }

    @EventHandler
    public void onInventoryClose(InventoryCloseEvent event) {
        if (!(event.getPlayer() instanceof Player player)) return;
        if (!isEligibleForBook(player)) return;

        if (recoverFromOpenContainer()) {
            InventoryType type = event.getView().getTopInventory().getType();
            if (type != InventoryType.CRAFTING && type != InventoryType.CREATIVE) {
                boolean owned = hasOwnedBook(player);
                recoverExternalBooks(player, event.getView().getTopInventory(), owned,
                        removeDuplicatesEnabled(), false);
            }
        }
        scheduleRepair(player);
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (!(event.getWhoClicked() instanceof Player player)) return;
        if (!isEligibleForBook(player) || !preventExternalStorage()) return;

        boolean cursorBook = isMemberBook(event.getCursor());
        boolean currentBook = isMemberBook(event.getCurrentItem());
        boolean clickedOwnInventory = event.getClickedInventory() == player.getInventory();
        boolean clickedForeignInventory = event.getClickedInventory() != null && !clickedOwnInventory;
        boolean touchedBook = cursorBook || currentBook;

        if (bookMode() == BookMode.LOCKED_HOTBAR) {
            int lockedHotbarButton = event.getHotbarButton();
            boolean reservedHotbarSwap = lockedHotbarButton == reservedSlot()
                    && isMemberBook(player.getInventory().getItem(reservedSlot()));
            if (touchedBook || reservedHotbarSwap) {
                event.setCancelled(true);
                scheduleRepair(player);
                return;
            }
        }

        if (cursorBook && clickedForeignInventory) {
            event.setCancelled(true);
            denyExternalStorage(player);
            scheduleRepair(player);
            return;
        }

        if (currentBook && clickedOwnInventory && event.isShiftClick() && hasExternalTopInventory(event)) {
            event.setCancelled(true);
            denyExternalStorage(player);
            scheduleRepair(player);
            return;
        }

        int hotbarButton = event.getHotbarButton();
        if (clickedForeignInventory && hotbarButton >= 0
                && isMemberBook(player.getInventory().getItem(hotbarButton))) {
            event.setCancelled(true);
            denyExternalStorage(player);
            scheduleRepair(player);
            return;
        }

        if (clickedForeignInventory && event.getClick() == ClickType.SWAP_OFFHAND
                && isMemberBook(player.getInventory().getItemInOffHand())) {
            event.setCancelled(true);
            denyExternalStorage(player);
            scheduleRepair(player);
            return;
        }

        if (event.getClickedInventory() == null && cursorBook
                && plugin.getConfig().getBoolean("member-book.prevent-drop", true)) {
            event.setCancelled(true);
            plugin.message(player, "member-book-cannot-drop");
            scheduleRepair(player);
            return;
        }

        if (touchedBook) scheduleRepair(player);
    }

    @EventHandler
    public void onInventoryDrag(InventoryDragEvent event) {
        if (!(event.getWhoClicked() instanceof Player player)) return;
        if (!isEligibleForBook(player)) return;
        if (!isMemberBook(event.getOldCursor())) return;
        if (bookMode() == BookMode.LOCKED_HOTBAR) {
            event.setCancelled(true);
            scheduleRepair(player);
            return;
        }
        if (!preventExternalStorage()) return;

        int topSize = event.getView().getTopInventory().getSize();
        for (int rawSlot : event.getRawSlots()) {
            if (rawSlot < topSize) {
                event.setCancelled(true);
                denyExternalStorage(player);
                scheduleRepair(player);
                return;
            }
        }

        scheduleRepair(player);
    }

    @EventHandler
    public void onInventoryMove(InventoryMoveItemEvent event) {
        if (bookMode() != BookMode.NORMAL && isMemberBook(event.getItem())) event.setCancelled(true);
    }

    @EventHandler
    public void onInventoryPickup(InventoryPickupItemEvent event) {
        if (bookMode() != BookMode.NORMAL && isMemberBook(event.getItem().getItemStack())) event.setCancelled(true);
    }

    @EventHandler
    public void onDispense(BlockDispenseEvent event) {
        if (bookMode() != BookMode.NORMAL && isMemberBook(event.getItem())) event.setCancelled(true);
    }

    @EventHandler
    public void onEntityPickup(EntityPickupItemEvent event) {
        if (!(event.getEntity() instanceof Player player)) return;
        Item itemEntity = event.getItem();
        if (!isMemberBook(itemEntity.getItemStack())) return;
        if (bookMode() == BookMode.NORMAL) return;

        event.setCancelled(true);
        ItemStack recovered = itemEntity.getItemStack().clone();
        itemEntity.remove();

        if (!isEligibleForBook(player) || recoverySuppressed.contains(player.getUniqueId())) return;
        if (!hasOwnedBook(player)) placeBookInPlayer(player, recovered);
        scheduleRepair(player);
    }

    @EventHandler
    public void onDrop(PlayerDropItemEvent event) {
        if (!isEligibleForBook(event.getPlayer())) return;
        if (bookMode() == BookMode.NORMAL) return;
        if (!plugin.getConfig().getBoolean("member-book.prevent-drop", true)) return;
        if (!isMemberBook(event.getItemDrop().getItemStack())) return;
        event.setCancelled(true);
        plugin.message(event.getPlayer(), "member-book-cannot-drop");
        scheduleRepair(event.getPlayer());
    }

    @EventHandler
    public void onDeath(PlayerDeathEvent event) {
        if (!isEnabled() || bookMode() == BookMode.NORMAL) return;
        event.getDrops().removeIf(this::isMemberBook);
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
        menuOpenCooldown.remove(player.getUniqueId());
        fixedSlotReturnPending.remove(player.getUniqueId());
        if (bookMode() == BookMode.NORMAL) return;
        if (!isMemberBook(player.getItemOnCursor())) return;

        if (hasInventoryBook(player)) {
            player.setItemOnCursor(null);
            return;
        }

        ItemStack cursorBook = player.getItemOnCursor().clone();
        if (placeBookInPlayer(player, cursorBook)) player.setItemOnCursor(null);
    }

    private boolean hasInventoryBook(Player player) {
        for (ItemStack item : player.getInventory().getContents()) {
            if (isMemberBook(item)) return true;
        }
        return false;
    }

    private enum BookMode {
        MOVABLE,
        LOCKED_HOTBAR,
        FIXED_SLOT_MOVABLE,
        NORMAL
    }
}
