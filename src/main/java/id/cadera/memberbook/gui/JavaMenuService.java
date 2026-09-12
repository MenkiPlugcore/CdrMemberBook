package id.cadera.memberbook.gui;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.SkullMeta;
import org.bukkit.persistence.PersistentDataType;
import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.menu.MenuConfigService.MenuButton;
import id.cadera.memberbook.menu.MenuConfigService.MenuDefinition;
import id.cadera.memberbook.tp.TeleportMode;
import id.cadera.memberbook.util.Colors;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

public final class JavaMenuService implements Listener {
    private static final int PAGE_SIZE = 45;
    private static final String NAV_BACK = "__back";
    private static final String NAV_PREVIOUS = "__previous";
    private static final String NAV_NEXT = "__next";

    private final CdrMemberBookPlugin plugin;

    public JavaMenuService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    public void showMain(Player player) {
        showConfiguredMenu(player, "main", 0);
    }

    public void showConfiguredMenu(Player player, String menuId, int requestedPage) {
        MenuDefinition menu = plugin.menus().getMenu(menuId);
        if (menu == null) {
            plugin.message(player, "menu-not-found", "%menu%", menuId == null ? "main" : menuId);
            if (!"main".equalsIgnoreCase(menuId)) showMain(player);
            return;
        }

        List<MenuButton> buttons = plugin.menus().visibleButtons(menu, player);
        int totalPages = Math.max(1, (buttons.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = Math.max(0, Math.min(requestedPage, totalPages - 1));
        int start = page * PAGE_SIZE;
        int end = Math.min(buttons.size(), start + PAGE_SIZE);
        List<MenuButton> pageButtons = buttons.subList(start, end);

        boolean navigationRow = !menu.id().equals("main") || totalPages > 1;
        int contentRows = Math.max(1, (pageButtons.size() + 8) / 9);
        int size = Math.min(54, (contentRows + (navigationRow ? 1 : 0)) * 9);

        String title = plugin.formatMenuText(menu.title(), player);
        MenuHolder holder = new MenuHolder(MenuHolder.Type.CONFIG, null, menu.id(), page, size, title);
        Inventory inventory = holder.getInventory();

        int slot = 0;
        for (MenuButton button : pageButtons) {
            inventory.setItem(slot++, configuredItem(button, player));
        }

        if (navigationRow) {
            int navBase = size - 9;
            if (page > 0) inventory.setItem(navBase, navigationItem(Material.ARROW, "Halaman Sebelumnya", NAV_PREVIOUS));
            if (!menu.id().equals("main")) inventory.setItem(navBase + 4, navigationItem(Material.BARRIER, "Kembali", NAV_BACK));
            if (page < totalPages - 1) inventory.setItem(navBase + 8, navigationItem(Material.ARROW, "Halaman Berikutnya", NAV_NEXT));
        }

        player.openInventory(inventory);
    }

    public void showPlayerSelect(Player player) {
        showPlayerSelect(player, "main", 0);
    }

    private void showPlayerSelect(Player player, String returnMenuId, int requestedPage) {
        List<? extends Player> players = Bukkit.getOnlinePlayers().stream()
                .filter(other -> !other.getUniqueId().equals(player.getUniqueId()))
                .toList();
        if (players.isEmpty()) {
            plugin.message(player, "no-other-players");
            showConfiguredMenu(player, returnMenuId, 0);
            return;
        }

        int totalPages = Math.max(1, (players.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = Math.max(0, Math.min(requestedPage, totalPages - 1));
        int start = page * PAGE_SIZE;
        int end = Math.min(players.size(), start + PAGE_SIZE);
        int visiblePlayers = end - start;
        int playerRows = Math.max(1, (visiblePlayers + 8) / 9);
        int size = Math.min(54, (playerRows + 1) * 9);

        MenuHolder holder = new MenuHolder(MenuHolder.Type.PLAYER_SELECT, null, returnMenuId, page, size, "Pilih Player");
        Inventory inventory = holder.getInventory();
        int slot = 0;
        for (int i = start; i < end; i++) {
            Player target = players.get(i);
            ItemStack head = new ItemStack(Material.PLAYER_HEAD);
            SkullMeta meta = (SkullMeta) head.getItemMeta();
            meta.setDisplayName("§b" + target.getName());
            meta.setOwningPlayer(target);
            meta.getPersistentDataContainer().set(plugin.playerKey(), PersistentDataType.STRING, target.getUniqueId().toString());
            head.setItemMeta(meta);
            inventory.setItem(slot++, head);
        }

        int navBase = size - 9;
        if (page > 0) inventory.setItem(navBase, navigationItem(Material.ARROW, "Halaman Sebelumnya", NAV_PREVIOUS));
        inventory.setItem(navBase + 4, navigationItem(Material.BARRIER, "Kembali", NAV_BACK));
        if (page < totalPages - 1) inventory.setItem(navBase + 8, navigationItem(Material.ARROW, "Halaman Berikutnya", NAV_NEXT));
        player.openInventory(inventory);
    }

    private void showMode(Player player, Player target, String returnMenuId) {
        MenuHolder holder = new MenuHolder(MenuHolder.Type.TP_MODE, target.getUniqueId(), returnMenuId, 0, 9,
                "TP • " + target.getName());
        Inventory inventory = holder.getInventory();
        inventory.setItem(0, item(Material.ARROW, "Kembali"));
        inventory.setItem(3, item(Material.ENDER_PEARL, "Pergi ke " + target.getName()));
        inventory.setItem(5, item(Material.LEAD, "Bawa " + target.getName() + " ke saya"));
        inventory.setItem(8, item(plugin.requests().toggles().isDisabled(player.getUniqueId())
                ? Material.REDSTONE_BLOCK : Material.LIME_CONCRETE,
                "Incoming TP: " + (plugin.requests().toggles().isDisabled(player.getUniqueId()) ? "OFF" : "ON")));
        player.openInventory(inventory);
    }

    @EventHandler
    public void onClick(InventoryClickEvent event) {
        if (!(event.getInventory().getHolder() instanceof MenuHolder holder)) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player)) return;
        if (event.getClickedInventory() == null || event.getClickedInventory() != event.getInventory()) return;
        ItemStack clicked = event.getCurrentItem();
        if (clicked == null || clicked.getType().isAir()) return;

        switch (holder.type()) {
            case CONFIG -> handleConfiguredClick(player, holder, clicked);
            case PLAYER_SELECT -> handlePlayerSelectClick(player, holder, clicked);
            case TP_MODE -> handleTpMode(player, holder, event.getSlot());
        }
    }

    private void handleConfiguredClick(Player player, MenuHolder holder, ItemStack clicked) {
        ItemMeta meta = clicked.getItemMeta();
        String action = meta.getPersistentDataContainer().get(plugin.buttonKey(), PersistentDataType.STRING);
        if (action == null) return;

        if (NAV_PREVIOUS.equals(action)) {
            showConfiguredMenu(player, holder.menuId(), holder.page() - 1);
            return;
        }
        if (NAV_NEXT.equals(action)) {
            showConfiguredMenu(player, holder.menuId(), holder.page() + 1);
            return;
        }

        MenuDefinition menu = plugin.menus().getMenu(holder.menuId());
        if (menu == null) {
            showMain(player);
            return;
        }
        if (NAV_BACK.equals(action)) {
            showConfiguredMenu(player, menu.backMenu(), 0);
            return;
        }

        MenuButton button = plugin.menus().findButton(menu, action);
        if (button == null) return;
        if (!plugin.menus().canUse(player, button)) {
            plugin.message(player, "no-permission");
            return;
        }
        if (!plugin.menus().isAvailable(player, button)) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, holder.menuId(), holder.page());
            return;
        }

        if (button.actions() != null && !button.actions().isEmpty()) {
            plugin.menuActions().execute(player, button.actions());
            return;
        }

        switch (button.type().toLowerCase(Locale.ROOT)) {
            case "command" -> {
                player.closeInventory();
                plugin.executeMenuCommand(player, button);
            }
            case "homes", "pay", "trade", "report" -> {
                // The rich click-only flows are Bedrock Forms. Java keeps the configured command as fallback.
                player.closeInventory();
                plugin.executeMenuCommand(player, button);
            }
            case "teleport" -> showPlayerSelect(player, menu.id(), 0);
            case "submenu" -> {
                if (button.submenu() == null || button.submenu().isBlank()) {
                    plugin.message(player, "menu-not-found", "%menu%", button.key());
                    return;
                }
                showConfiguredMenu(player, button.submenu(), 0);
            }
            case "close" -> player.closeInventory();
            default -> plugin.message(player, "invalid-button-type", "%type%", button.type());
        }
    }

    private void handlePlayerSelectClick(Player player, MenuHolder holder, ItemStack clicked) {
        ItemMeta meta = clicked.getItemMeta();
        String nav = meta.getPersistentDataContainer().get(plugin.buttonKey(), PersistentDataType.STRING);
        if (NAV_PREVIOUS.equals(nav)) {
            showPlayerSelect(player, holder.menuId(), holder.page() - 1);
            return;
        }
        if (NAV_NEXT.equals(nav)) {
            showPlayerSelect(player, holder.menuId(), holder.page() + 1);
            return;
        }
        if (NAV_BACK.equals(nav)) {
            showConfiguredMenu(player, holder.menuId(), 0);
            return;
        }

        String raw = meta.getPersistentDataContainer().get(plugin.playerKey(), PersistentDataType.STRING);
        if (raw == null) return;
        try {
            Player target = Bukkit.getPlayer(UUID.fromString(raw));
            if (target == null) {
                plugin.message(player, "player-not-found");
                showPlayerSelect(player, holder.menuId(), holder.page());
                return;
            }
            showMode(player, target, holder.menuId());
        } catch (IllegalArgumentException ignored) {
        }
    }

    private void handleTpMode(Player player, MenuHolder holder, int slot) {
        if (slot == 0) {
            showPlayerSelect(player, holder.menuId(), 0);
            return;
        }
        if (slot == 8) {
            boolean disabled = plugin.requests().toggles().toggle(player.getUniqueId());
            plugin.message(player, disabled ? "toggle-off" : "toggle-on");
            Player target = holder.targetId() == null ? null : Bukkit.getPlayer(holder.targetId());
            if (target != null) showMode(player, target, holder.menuId());
            else showPlayerSelect(player, holder.menuId(), 0);
            return;
        }
        if (holder.targetId() == null) return;
        Player target = Bukkit.getPlayer(holder.targetId());
        if (target == null) {
            plugin.message(player, "player-not-found");
            showPlayerSelect(player, holder.menuId(), 0);
            return;
        }
        if (slot == 3) {
            plugin.requests().create(player, target, TeleportMode.TO_TARGET);
            player.closeInventory();
        } else if (slot == 5) {
            plugin.requests().create(player, target, TeleportMode.TARGET_TO_REQUESTER);
            player.closeInventory();
        }
    }

    private ItemStack configuredItem(MenuButton button, Player player) {
        Material material = Material.matchMaterial(button.javaMaterial() == null ? "PAPER" : button.javaMaterial());
        if (material == null || material.isAir()) material = Material.PAPER;
        ItemStack item = new ItemStack(material);
        ItemMeta meta = item.getItemMeta();
        meta.setDisplayName(plugin.formatMenuText(button.name(), player));

        if (button.lore() != null && !button.lore().isEmpty()) {
            List<String> lore = new ArrayList<>();
            for (String line : button.lore()) lore.add(plugin.formatMenuText(line, player));
            meta.setLore(lore);
        }
        meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, button.key());
        item.setItemMeta(meta);
        return item;
    }

    private ItemStack navigationItem(Material material, String name, String action) {
        ItemStack item = item(material, name);
        ItemMeta meta = item.getItemMeta();
        meta.getPersistentDataContainer().set(plugin.buttonKey(), PersistentDataType.STRING, action);
        item.setItemMeta(meta);
        return item;
    }

    private ItemStack item(Material material, String name) {
        ItemStack item = new ItemStack(material);
        ItemMeta meta = item.getItemMeta();
        meta.setDisplayName(Colors.legacy("&f" + name));
        item.setItemMeta(meta);
        return item;
    }
}
