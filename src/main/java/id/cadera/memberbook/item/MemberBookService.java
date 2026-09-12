package id.cadera.memberbook.item;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.event.player.PlayerDropItemEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerRespawnEvent;
import org.bukkit.event.player.PlayerSwapHandItemsEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Colors;

import java.util.ArrayList;
import java.util.List;

public final class MemberBookService implements Listener {
    private static final int STORAGE_END = 35;

    private final CdrMemberBookPlugin plugin;
    private final NamespacedKey bookKey;

    public MemberBookService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.bookKey = new NamespacedKey(plugin, "member-book");
    }

    public void startEnforcement() {
        long period = Math.max(5L, plugin.getConfig().getLong("member-book.enforce-interval-ticks", 20L));
        Bukkit.getScheduler().runTaskTimer(plugin, () -> {
            for (Player player : Bukkit.getOnlinePlayers()) {
                syncBookState(player);
            }
        }, period, period);
    }

    public void giveToOnlinePlayers() {
        if (!isEnabled()) return;
        for (Player player : Bukkit.getOnlinePlayers()) {
            syncBookState(player);
        }
    }

    public void ensureBook(Player player) {
        if (!isEligible(player) || !shouldMaintain()) return;

        if (isPermanentHotbar()) {
            ensureLockedHotbarBook(player);
        } else {
            ensureRegularBook(player);
        }
    }

    public boolean isMemberBook(ItemStack item) {
        if (item == null || item.getType().isAir() || !item.hasItemMeta()) return false;
        Byte marker = item.getItemMeta().getPersistentDataContainer().get(bookKey, PersistentDataType.BYTE);
        return marker != null && marker == (byte) 1;
    }

    private void syncBookState(Player player) {
        if (!isEnabled()) return;

        if (!isEligible(player)) {
            if (isBedrockOnly()) removeAllBooks(player);
            return;
        }

        ensureBook(player);
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

    private void ensureRegularBook(Player player) {
        if (hasBook(player)) return;

        ItemStack book = createBook();
        int slot = reservedSlot();
        ItemStack current = player.getInventory().getItem(slot);

        if (current == null || current.getType().isAir()) {
            player.getInventory().setItem(slot, book);
            return;
        }

        if (!player.getInventory().addItem(book).isEmpty()) {
            plugin.message(player, "member-book-inventory-full");
        }
    }

    private int findStorageBookSlot(PlayerInventory inventory, int excludedSlot) {
        for (int slot = 0; slot <= STORAGE_END; slot++) {
            if (slot == excludedSlot) continue;
            if (isMemberBook(inventory.getItem(slot))) return slot;
        }
        return -1;
    }

    private int findFreeStorageSlot(PlayerInventory inventory, int excludedSlot) {
        // Prefer the main inventory so the reserved book does not reshuffle the rest of the hotbar.
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

    private void removeAllBooks(Player player) {
        PlayerInventory inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getSize(); slot++) {
            if (isMemberBook(inventory.getItem(slot))) inventory.setItem(slot, null);
        }
    }

    private boolean hasBook(Player player) {
        for (ItemStack item : player.getInventory().getContents()) {
            if (isMemberBook(item)) return true;
        }
        return false;
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

    private boolean isEligible(Player player) {
        if (!isEnabled()) return false;
        if (!isBedrockOnly()) return true;
        return plugin.forms() != null && plugin.forms().isBedrock(player);
    }

    private boolean shouldMaintain() {
        return plugin.getConfig().getBoolean("member-book.permanent-hotbar", true)
                || plugin.getConfig().getBoolean("member-book.give-on-join", true);
    }

    private boolean isPermanentHotbar() {
        return plugin.getConfig().getBoolean("member-book.permanent-hotbar", true);
    }

    private boolean preventMove() {
        return plugin.getConfig().getBoolean("member-book.prevent-move", true);
    }

    private int reservedSlot() {
        int configuredSlot = plugin.getConfig().getInt("member-book.hotbar-slot", 8);
        return Math.max(0, Math.min(8, configuredSlot));
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        if (!isEnabled()) return;
        long delay = Math.max(1L, plugin.getConfig().getLong("member-book.give-delay-ticks", 10L));
        Player player = event.getPlayer();
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) syncBookState(player);
        }, delay);
    }

    @EventHandler
    public void onRespawn(PlayerRespawnEvent event) {
        if (!isEnabled()) return;
        Player player = event.getPlayer();
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) syncBookState(player);
        }, 1L);
    }

    @EventHandler
    public void onInteract(PlayerInteractEvent event) {
        if (!isEligible(event.getPlayer()) || event.getHand() != EquipmentSlot.HAND) return;
        Action action = event.getAction();
        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;
        if (!isMemberBook(event.getItem())) return;

        event.setCancelled(true);
        plugin.openMenu(event.getPlayer());
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (!(event.getWhoClicked() instanceof Player player)) return;
        if (!isEligible(player) || !preventMove()) return;

        int reserved = reservedSlot();
        boolean clickedReserved = isPermanentHotbar()
                && event.getClickedInventory() == player.getInventory()
                && event.getSlot() == reserved;
        boolean hotbarSwapTouchesReserved = isPermanentHotbar() && event.getHotbarButton() == reserved;
        boolean touchesBook = isMemberBook(event.getCurrentItem()) || isMemberBook(event.getCursor());

        if (clickedReserved || hotbarSwapTouchesReserved || touchesBook) {
            event.setCancelled(true);
            Bukkit.getScheduler().runTask(plugin, () -> {
                if (player.isOnline()) ensureBook(player);
            });
        }
    }

    @EventHandler
    public void onInventoryDrag(InventoryDragEvent event) {
        if (!(event.getWhoClicked() instanceof Player player)) return;
        if (!isEligible(player) || !preventMove()) return;

        if (isMemberBook(event.getOldCursor())) {
            event.setCancelled(true);
            return;
        }

        if (!isPermanentHotbar()) return;
        int reserved = reservedSlot();
        int topSize = event.getView().getTopInventory().getSize();
        for (int rawSlot : event.getRawSlots()) {
            if (rawSlot >= topSize && event.getView().convertSlot(rawSlot) == reserved) {
                event.setCancelled(true);
                Bukkit.getScheduler().runTask(plugin, () -> {
                    if (player.isOnline()) ensureBook(player);
                });
                return;
            }
        }
    }

    @EventHandler
    public void onSwapHands(PlayerSwapHandItemsEvent event) {
        if (!isEligible(event.getPlayer()) || !preventMove()) return;
        if (isMemberBook(event.getMainHandItem()) || isMemberBook(event.getOffHandItem())) {
            event.setCancelled(true);
        }
    }

    @EventHandler
    public void onDrop(PlayerDropItemEvent event) {
        if (!isEligible(event.getPlayer())) return;
        if (!plugin.getConfig().getBoolean("member-book.prevent-drop", true)) return;
        if (!isMemberBook(event.getItemDrop().getItemStack())) return;
        event.setCancelled(true);
        plugin.message(event.getPlayer(), "member-book-cannot-drop");
    }

    @EventHandler
    public void onDeath(PlayerDeathEvent event) {
        if (!isEnabled()) return;
        event.getDrops().removeIf(this::isMemberBook);
    }
}
