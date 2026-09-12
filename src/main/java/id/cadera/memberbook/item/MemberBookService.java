package id.cadera.memberbook.item;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Colors;
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
import org.bukkit.event.inventory.Inventory;
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
    private BukkitTask enforcementTask;

    public MemberBookService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.bookKey = new NamespacedKey(plugin, "member-book");
    }

    public void startEnforcement() {
        stopEnforcement();
        if (!isEnabled()) return;
        if (!isPermanentHotbar() && !recoveryEnabled()) return;

        long configuredPeriod = isPermanentHotbar()
                ? plugin.getConfig().getLong("member-book.enforce-interval-ticks", 20L)
                : plugin.getConfig().getLong("member-book.recovery.interval-ticks", 100L);
        long period = Math.max(20L, configuredPeriod);

        enforcementTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
            for (Player player : Bukkit.getOnlinePlayers()) {
                syncBookState(player, false);
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
    }

    public void giveToOnlinePlayers() {
        if (!isEnabled()) return;
        for (Player player : Bukkit.getOnlinePlayers()) {
            syncBookState(player, false);
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
        return reconcileMovableBook(player, true, true, true) && finishLockedMode(player);
    }

    public boolean forceRepair(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        boolean repaired = reconcileMovableBook(player, true, true, true);
        if (!repaired) return false;
        return finishLockedMode(player);
    }

    public int forceRemove(Player player) {
        recoverySuppressed.add(player.getUniqueId());
        return removeAllVisibleBooks(player, true);
    }

    private boolean finishLockedMode(Player player) {
        if (!isPermanentHotbar()) return hasOwnedBook(player);
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

        if (isPermanentHotbar()) {
            // First sanitize duplicates/cursor/open-container state without creating a new copy.
            reconcileMovableBook(player, false, false, false);
            // Never create while the legitimate book is temporarily on the cursor.
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
            hasOwned = placeBookInPlayer(player, createBook());
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

        // If the player already owns a legitimate copy, all visible external copies are invalid duplicates.
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
        ItemStack book = sourceSlot >= 0 ? inventory.getItem(sourceSlot) : createBook();
        if (book == null) book = createBook();

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

    private ItemStack createBook() {
        String materialName = plugin.getConfig().getString("member-book.material", "BOOK");
        Material material = materialName == null ? Material.BOOK : Material.matchMaterial(materialName);
        if (material == null) material = Material.BOOK;

        ItemStack item = new ItemStack(material);
        ItemMeta meta = item.getItemMeta();
        meta.setDisplayName(Colors.legacy(plugin.getConfig().getString(
                "member-book.name", "&d&lMOONSIGN &fMember Book")));

        List<String> lore = new ArrayList<>();
        for (String line : plugin.getConfig().getStringList("member-book.lore")) {
            lore.add(Colors.legacy(line));
        }
        if (!lore.isEmpty()) meta.setLore(lore);

        meta.getPersistentDataContainer().set(bookKey, PersistentDataType.BYTE, (byte) 1);
        item.setItemMeta(meta);
        return item;
    }

    private boolean isEnabled() {
        return plugin.getConfig().getBoolean("member-book.enabled", true);
    }

    private boolean isBedrockOnly() {
        return plugin.getConfig().getBoolean("member-book.bedrock-only", true);
    }

    private boolean shouldMaintain() {
        return isPermanentHotbar() || plugin.getConfig().getBoolean("member-book.give-on-join", true);
    }

    private boolean isPermanentHotbar() {
        return plugin.getConfig().getBoolean("member-book.permanent-hotbar", false);
    }

    private boolean preventExternalStorage() {
        return plugin.getConfig().getBoolean("member-book.prevent-external-storage", true);
    }

    private boolean recoveryEnabled() {
        return plugin.getConfig().getBoolean("member-book.recovery.enabled", true);
    }

    private boolean recoverFromOpenContainer() {
        return plugin.getConfig().getBoolean("member-book.recovery.recover-from-open-container", true);
    }

    private boolean removeDuplicatesEnabled() {
        return plugin.getConfig().getBoolean("member-book.recovery.remove-duplicates", true);
    }

    private boolean recoverOnWorldChange() {
        return plugin.getConfig().getBoolean("member-book.recovery.recover-on-world-change", true);
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
            if (player.isOnline()) syncBookState(player, true);
        }, delay);
    }

    @EventHandler
    public void onRespawn(PlayerRespawnEvent event) {
        if (!isEnabled()) return;
        Player player = event.getPlayer();
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) syncBookState(player, true);
        }, 1L);
    }

    @EventHandler
    public void onWorldChange(PlayerChangedWorldEvent event) {
        if (!recoverOnWorldChange()) return;
        Player player = event.getPlayer();
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) syncBookState(player, false);
        }, 1L);
    }

    @EventHandler
    public void onInteract(PlayerInteractEvent event) {
        if (!isEligibleForBook(event.getPlayer())) return;
        Action action = event.getAction();
        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;
        if (!isMemberBook(event.getItem())) return;

        event.setCancelled(true);
        plugin.openMenu(event.getPlayer());
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
        if (!isEligibleForBook(player) || !preventExternalStorage()) return;
        if (!isMemberBook(event.getOldCursor())) return;

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
        if (isMemberBook(event.getItem())) event.setCancelled(true);
    }

    @EventHandler
    public void onInventoryPickup(InventoryPickupItemEvent event) {
        if (isMemberBook(event.getItem().getItemStack())) event.setCancelled(true);
    }

    @EventHandler
    public void onDispense(BlockDispenseEvent event) {
        if (isMemberBook(event.getItem())) event.setCancelled(true);
    }

    @EventHandler
    public void onEntityPickup(EntityPickupItemEvent event) {
        if (!(event.getEntity() instanceof Player player)) return;
        Item itemEntity = event.getItem();
        if (!isMemberBook(itemEntity.getItemStack())) return;

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
        if (!plugin.getConfig().getBoolean("member-book.prevent-drop", true)) return;
        if (!isMemberBook(event.getItemDrop().getItemStack())) return;
        event.setCancelled(true);
        plugin.message(event.getPlayer(), "member-book-cannot-drop");
        scheduleRepair(event.getPlayer());
    }

    @EventHandler
    public void onDeath(PlayerDeathEvent event) {
        if (!isEnabled()) return;
        event.getDrops().removeIf(this::isMemberBook);
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
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
}
