package id.cadera.memberbook.admin;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Colors;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryType;
import org.bukkit.event.inventory.PrepareAnvilEvent;
import org.bukkit.inventory.AnvilInventory;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.geysermc.cumulus.form.CustomForm;
import org.geysermc.cumulus.form.Form;
import org.geysermc.cumulus.form.ModalForm;
import org.geysermc.cumulus.form.SimpleForm;
import org.geysermc.floodgate.api.FloodgateApi;
import org.jetbrains.annotations.NotNull;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

public final class AdminMenuEditorService implements Listener {
    private static final String DEFAULT_PERMISSION = "cdrmemberbook.admin.memberbook";
    private static final Pattern KEY_PATTERN = Pattern.compile("[a-z0-9_-]{1,32}");
    private static final List<String> TYPES = List.of("command", "teleport", "homes", "pay", "trade", "report", "report-center", "settings", "submenu", "close");
    private static final List<String> PLATFORMS = List.of("ANY", "JAVA", "BEDROCK");
    private static final int[] GRID = {10,11,12,13,14,15,16,19,20,21,22,23,24,25,28,29,30,31,32,33,34,37,38,39,40,41,42,43};
    private static final int PAGE_SIZE = GRID.length;

    private static final String A_BACK = "editor:back";
    private static final String A_CLOSE = "editor:close";
    private static final String A_PREV = "editor:prev";
    private static final String A_NEXT = "editor:next";
    private static final String A_ADD = "editor:add";
    private static final String A_TOGGLE = "editor:toggle";
    private static final String A_TYPE = "editor:type";
    private static final String A_PLATFORM = "editor:platform";
    private static final String A_ADVANCED = "editor:advanced";
    private static final String A_DELETE = "editor:delete";
    private static final String A_DELETE_CONFIRM = "editor:delete-confirm";
    private static final String A_PREVIEW = "editor:preview";
    private static final String MENU_PREFIX = "editor:menu:";
    private static final String BUTTON_PREFIX = "editor:button:";
    private static final String FIELD_PREFIX = "editor:field:";

    private static final String F_NEW_KEY = "new-key";
    private static final String F_NAME = "name";
    private static final String F_COMMAND = "command";
    private static final String F_MATERIAL = "java-material";
    private static final String F_ICON = "icon";
    private static final String F_PERMISSION = "permission";
    private static final String F_ORDER = "order";
    private static final String F_SUBMENU = "submenu";
    private static final String F_LORE = "lore";
    private static final String F_REQUIRES_COMMAND = "requires-command";
    private static final String F_REQUIRES_PLUGINS = "requires-plugins";
    private static final String F_WORLDS = "worlds";
    private static final String F_EXCLUDED_WORLDS = "excluded-worlds";
    private static final String F_CONDITION_PERMISSIONS = "condition-permissions";
    private static final String F_MIN_ONLINE = "min-online";
    private static final String F_MAX_ONLINE = "max-online";

    private final CdrMemberBookPlugin plugin;

    public AdminMenuEditorService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    public void open(Player player) {
        if (!allowed(player)) return;
        if (!plugin.getConfig().getBoolean("admin-menu-editor.enabled", true)) {
            player.sendMessage(Colors.legacy("&eAdmin Menu Editor sedang dinonaktifkan di config."));
            return;
        }
        if (isBedrock(player)) showBedrockRoot(player);
        else showJavaRoot(player, 0);
    }

    private boolean allowed(Player player) {
        String permission = plugin.getConfig().getString("admin-menu-editor.permission", DEFAULT_PERMISSION);
        if (permission == null || permission.isBlank() || player.hasPermission(permission)) return true;
        plugin.message(player, "no-permission");
        return false;
    }

    private boolean isBedrock(Player player) {
        return plugin.forms() != null && plugin.forms().isBedrock(player);
    }

    // ---------------- Java GUI ----------------

    private void showJavaRoot(Player player, int requestedPage) {
        if (!allowed(player)) return;
        List<String> menus = menuIds();
        int pages = Math.max(1, (menus.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = clampPage(requestedPage, pages);
        EditorHolder holder = new EditorHolder(View.ROOT, null, null, null, page, 54, "§8Admin §7• §dMenu Editor");
        Inventory inv = holder.getInventory();
        decorate(inv);
        inv.setItem(4, item(Material.COMPARATOR, "&d&lAdmin Menu Editor", List.of("&7Pilih menu yang ingin diedit.", "&7Menu: &f" + menus.size())));
        int start = page * PAGE_SIZE;
        int end = Math.min(menus.size(), start + PAGE_SIZE);
        for (int i = start, slot = 0; i < end; i++, slot++) {
            String id = menus.get(i);
            int buttons = buttonKeys(id).size();
            inv.setItem(GRID[slot], actionItem(Material.BOOK, "&f" + id, MENU_PREFIX + id,
                    List.of("&7Buttons: &f" + buttons, "", "&8» &fKlik untuk kelola.")));
        }
        if (page > 0) inv.setItem(45, actionItem(Material.ARROW, "&eSebelumnya", A_PREV, List.of()));
        inv.setItem(49, actionItem(Material.BARRIER, "&cTutup", A_CLOSE, List.of("&7Tutup editor.")));
        if (page < pages - 1) inv.setItem(53, actionItem(Material.ARROW, "&eBerikutnya", A_NEXT, List.of()));
        player.openInventory(inv);
    }

    private void showJavaMenu(Player player, String menuId, int requestedPage) {
        if (!allowed(player) || !menuExists(menuId)) { showJavaRoot(player, 0); return; }
        List<String> keys = buttonKeys(menuId);
        int pages = Math.max(1, (keys.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = clampPage(requestedPage, pages);
        EditorHolder holder = new EditorHolder(View.MENU, menuId, null, null, page, 54, trim("§8Editor §7• §f" + menuId));
        Inventory inv = holder.getInventory();
        decorate(inv);
        inv.setItem(4, item(Material.WRITABLE_BOOK, "&d&l" + menuId, List.of("&7Buttons: &f" + keys.size(), "&7config: &f" + menuPath(menuId))));
        int start = page * PAGE_SIZE;
        int end = Math.min(keys.size(), start + PAGE_SIZE);
        for (int i = start, slot = 0; i < end; i++, slot++) {
            String key = keys.get(i);
            String base = buttonPath(menuId, key);
            boolean enabled = plugin.getConfig().getBoolean(base + ".enabled", true);
            String type = plugin.getConfig().getString(base + ".type", "command");
            String name = plugin.getConfig().getString(base + ".name", key);
            inv.setItem(GRID[slot], actionItem(enabled ? Material.LIME_DYE : Material.GRAY_DYE,
                    (enabled ? "&a" : "&7") + key, BUTTON_PREFIX + key,
                    List.of("&7Name: &f" + safe(name), "&7Type: &f" + safe(type), "&7Enabled: &f" + enabled, "", "&8» &fKlik untuk edit.")));
        }
        if (page > 0) inv.setItem(45, actionItem(Material.ARROW, "&eSebelumnya", A_PREV, List.of()));
        inv.setItem(48, actionItem(Material.OAK_DOOR, "&eDaftar Menu", A_BACK, List.of()));
        inv.setItem(50, actionItem(Material.ANVIL, "&aTambah Button", A_ADD, List.of("&7Buat button baru di menu ini.")));
        if (page < pages - 1) inv.setItem(53, actionItem(Material.ARROW, "&eBerikutnya", A_NEXT, List.of()));
        player.openInventory(inv);
    }

    private void showJavaButton(Player player, String menuId, String key) {
        if (!allowed(player) || !buttonExists(menuId, key)) { showJavaMenu(player, menuId, 0); return; }
        String base = buttonPath(menuId, key);
        EditorHolder holder = new EditorHolder(View.BUTTON, menuId, key, null, 0, 54, trim("§8Button §7• §f" + key));
        Inventory inv = holder.getInventory();
        decorate(inv);
        inv.setItem(4, buttonInfo(menuId, key));
        boolean enabled = plugin.getConfig().getBoolean(base + ".enabled", true);
        inv.setItem(10, actionItem(enabled ? Material.LIME_CONCRETE : Material.RED_CONCRETE,
                enabled ? "&aEnabled: ON" : "&cEnabled: OFF", A_TOGGLE, List.of("&7Klik untuk toggle.")));
        inv.setItem(11, actionItem(Material.REPEATER, "&eType: &f" + plugin.getConfig().getString(base + ".type", "command"), A_TYPE, List.of("&7Klik untuk ganti type.")));
        inv.setItem(12, fieldItem(Material.NAME_TAG, "&bName", F_NAME, current(menuId, key, F_NAME)));
        inv.setItem(13, fieldItem(Material.COMMAND_BLOCK, "&bCommand", F_COMMAND, current(menuId, key, F_COMMAND)));
        inv.setItem(14, fieldItem(Material.ITEM_FRAME, "&bJava Material", F_MATERIAL, current(menuId, key, F_MATERIAL)));
        inv.setItem(15, fieldItem(Material.PAINTING, "&bBedrock Icon", F_ICON, current(menuId, key, F_ICON)));
        inv.setItem(16, fieldItem(Material.TRIPWIRE_HOOK, "&bPermission", F_PERMISSION, current(menuId, key, F_PERMISSION)));
        inv.setItem(20, fieldItem(Material.CLOCK, "&bOrder", F_ORDER, current(menuId, key, F_ORDER)));
        inv.setItem(21, fieldItem(Material.OAK_DOOR, "&bSubmenu", F_SUBMENU, current(menuId, key, F_SUBMENU)));
        inv.setItem(22, fieldItem(Material.WRITABLE_BOOK, "&bLore", F_LORE, current(menuId, key, F_LORE)));
        inv.setItem(24, actionItem(Material.REDSTONE_TORCH, "&dDependencies & Conditions", A_ADVANCED,
                List.of("&7Required plugin/command, platform,", "&7world, permission, online count.")));
        inv.setItem(30, actionItem(Material.SPYGLASS, "&ePreview Menu", A_PREVIEW, List.of("&7Buka menu ini sebagai player.")));
        inv.setItem(32, actionItem(Material.BARRIER, "&cDelete Button", A_DELETE, List.of("&cMenghapus button dari config.")));
        inv.setItem(49, actionItem(Material.OAK_DOOR, "&eKembali", A_BACK, List.of("&7Kembali ke daftar button.")));
        player.openInventory(inv);
    }

    private void showJavaAdvanced(Player player, String menuId, String key) {
        if (!allowed(player) || !buttonExists(menuId, key)) { showJavaMenu(player, menuId, 0); return; }
        String base = buttonPath(menuId, key);
        EditorHolder holder = new EditorHolder(View.ADVANCED, menuId, key, null, 0, 54, trim("§8Advanced §7• §f" + key));
        Inventory inv = holder.getInventory();
        decorate(inv);
        inv.setItem(4, item(Material.REDSTONE_TORCH, "&d&lDependencies & Conditions", List.of("&7Button: &f" + key)));
        inv.setItem(10, fieldItem(Material.COMMAND_BLOCK, "&bRequires Command", F_REQUIRES_COMMAND, current(menuId,key,F_REQUIRES_COMMAND)));
        inv.setItem(11, fieldItem(Material.CHEST, "&bRequires Plugins", F_REQUIRES_PLUGINS, current(menuId,key,F_REQUIRES_PLUGINS)));
        String platform = plugin.getConfig().getString(base + ".conditions.platform", "ANY");
        inv.setItem(12, actionItem(Material.COMPASS, "&ePlatform: &f" + platform, A_PLATFORM, List.of("&7ANY → JAVA → BEDROCK")));
        inv.setItem(13, fieldItem(Material.GRASS_BLOCK, "&bWorlds", F_WORLDS, current(menuId,key,F_WORLDS)));
        inv.setItem(14, fieldItem(Material.BARRIER, "&bExcluded Worlds", F_EXCLUDED_WORLDS, current(menuId,key,F_EXCLUDED_WORLDS)));
        inv.setItem(15, fieldItem(Material.TRIPWIRE_HOOK, "&bExtra Permissions", F_CONDITION_PERMISSIONS, current(menuId,key,F_CONDITION_PERMISSIONS)));
        inv.setItem(16, fieldItem(Material.LIME_DYE, "&bMin Online", F_MIN_ONLINE, current(menuId,key,F_MIN_ONLINE)));
        inv.setItem(19, fieldItem(Material.RED_DYE, "&bMax Online", F_MAX_ONLINE, current(menuId,key,F_MAX_ONLINE)));
        inv.setItem(49, actionItem(Material.OAK_DOOR, "&eKembali", A_BACK, List.of("&7Kembali ke basic editor.")));
        player.openInventory(inv);
    }

    private void showJavaDelete(Player player, String menuId, String key) {
        EditorHolder holder = new EditorHolder(View.DELETE_CONFIRM, menuId, key, null, 0, 27, "§8Konfirmasi Delete");
        Inventory inv = holder.getInventory(); fill(inv, filler());
        inv.setItem(4, item(Material.WRITABLE_BOOK, "&c&lHapus " + key + "?", List.of("&7Menu: &f" + menuId, "&cTindakan ini langsung menyimpan config.")));
        inv.setItem(11, actionItem(Material.RED_CONCRETE, "&c&lHAPUS", A_DELETE_CONFIRM, List.of("&7Hapus permanen dari menu.")));
        inv.setItem(15, actionItem(Material.GRAY_CONCRETE, "&7BATAL", A_BACK, List.of()));
        player.openInventory(inv);
    }

    private void showJavaInput(Player player, String menuId, String key, String field) {
        String initial = field.equals(F_NEW_KEY) ? "" : current(menuId, key, field);
        String placeholder = placeholder(field);
        EditorHolder holder = new EditorHolder(View.INPUT, menuId, key, field, 0, InventoryType.ANVIL, trim("§8Edit §7• §f" + label(field)));
        AnvilInventory inv = (AnvilInventory) holder.getInventory();
        String shown = initial == null || initial.isBlank() ? placeholder : initial;
        inv.setItem(0, item(Material.PAPER, "&f" + shown, List.of("&7" + inputHint(field), "&7Gunakan &f- &7untuk mengosongkan field.")));
        inv.setRepairCost(0);
        player.openInventory(inv);
    }

    @EventHandler
    public void onPrepareAnvil(PrepareAnvilEvent event) {
        if (!(event.getInventory().getHolder() instanceof EditorHolder holder) || holder.view != View.INPUT) return;
        ItemStack input = event.getInventory().getItem(0);
        if (input == null || input.getType().isAir()) return;
        ItemStack result = input.clone();
        ItemMeta meta = result.getItemMeta();
        String rename = event.getInventory().getRenameText();
        meta.setDisplayName(Colors.legacy("&f" + (rename == null || rename.isBlank() ? placeholder(holder.field) : shorten(rename, 48))));
        result.setItemMeta(meta);
        event.setResult(result);
        event.getInventory().setRepairCost(0);
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (!(event.getInventory().getHolder() instanceof EditorHolder holder)) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player) || !allowed(player)) return;
        if (event.getClickedInventory() == null || event.getClickedInventory() != event.getInventory()) return;
        if (holder.view == View.INPUT) {
            if (event.getSlot() == 2 && event.getInventory() instanceof AnvilInventory anvil) {
                String value = anvil.getRenameText();
                if (value == null) value = "";
                if (value.trim().equalsIgnoreCase(placeholder(holder.field))) value = "";
                handleInput(player, holder, value);
            }
            return;
        }
        ItemStack clicked = event.getCurrentItem();
        String action = action(clicked);
        if (action == null) return;
        switch (holder.view) {
            case ROOT -> handleRootClick(player, holder, action);
            case MENU -> handleMenuClick(player, holder, action);
            case BUTTON -> handleButtonClick(player, holder, action);
            case ADVANCED -> handleAdvancedClick(player, holder, action);
            case DELETE_CONFIRM -> {
                if (A_DELETE_CONFIRM.equals(action)) { deleteButton(player, holder.menuId, holder.buttonKey); showJavaMenu(player, holder.menuId, 0); }
                else showJavaButton(player, holder.menuId, holder.buttonKey);
            }
            default -> { }
        }
    }

    private void handleRootClick(Player player, EditorHolder holder, String action) {
        if (A_CLOSE.equals(action)) { player.closeInventory(); return; }
        if (A_PREV.equals(action)) { showJavaRoot(player, holder.page - 1); return; }
        if (A_NEXT.equals(action)) { showJavaRoot(player, holder.page + 1); return; }
        if (action.startsWith(MENU_PREFIX)) showJavaMenu(player, action.substring(MENU_PREFIX.length()), 0);
    }

    private void handleMenuClick(Player player, EditorHolder holder, String action) {
        if (A_BACK.equals(action)) { showJavaRoot(player, 0); return; }
        if (A_PREV.equals(action)) { showJavaMenu(player, holder.menuId, holder.page - 1); return; }
        if (A_NEXT.equals(action)) { showJavaMenu(player, holder.menuId, holder.page + 1); return; }
        if (A_ADD.equals(action)) { showJavaInput(player, holder.menuId, null, F_NEW_KEY); return; }
        if (action.startsWith(BUTTON_PREFIX)) showJavaButton(player, holder.menuId, action.substring(BUTTON_PREFIX.length()));
    }

    private void handleButtonClick(Player player, EditorHolder holder, String action) {
        if (A_BACK.equals(action)) { showJavaMenu(player, holder.menuId, 0); return; }
        if (A_TOGGLE.equals(action)) { toggleEnabled(player, holder.menuId, holder.buttonKey); showJavaButton(player, holder.menuId, holder.buttonKey); return; }
        if (A_TYPE.equals(action)) { cycleType(player, holder.menuId, holder.buttonKey); showJavaButton(player, holder.menuId, holder.buttonKey); return; }
        if (A_ADVANCED.equals(action)) { showJavaAdvanced(player, holder.menuId, holder.buttonKey); return; }
        if (A_DELETE.equals(action)) { showJavaDelete(player, holder.menuId, holder.buttonKey); return; }
        if (A_PREVIEW.equals(action)) { plugin.openMenu(player, holder.menuId); return; }
        if (action.startsWith(FIELD_PREFIX)) showJavaInput(player, holder.menuId, holder.buttonKey, action.substring(FIELD_PREFIX.length()));
    }

    private void handleAdvancedClick(Player player, EditorHolder holder, String action) {
        if (A_BACK.equals(action)) { showJavaButton(player, holder.menuId, holder.buttonKey); return; }
        if (A_PLATFORM.equals(action)) { cyclePlatform(player, holder.menuId, holder.buttonKey); showJavaAdvanced(player, holder.menuId, holder.buttonKey); return; }
        if (action.startsWith(FIELD_PREFIX)) showJavaInput(player, holder.menuId, holder.buttonKey, action.substring(FIELD_PREFIX.length()));
    }

    private void handleInput(Player player, EditorHolder holder, String raw) {
        if (holder.field.equals(F_NEW_KEY)) {
            String key = raw.trim().toLowerCase(Locale.ROOT);
            if (!KEY_PATTERN.matcher(key).matches()) { error(player, "Key hanya a-z, 0-9, _ atau - (1-32 karakter)."); showJavaInput(player, holder.menuId, null, F_NEW_KEY); return; }
            if (buttonExists(holder.menuId, key)) { error(player, "Button key sudah ada: " + key); showJavaMenu(player, holder.menuId, 0); return; }
            if (buttonKeys(holder.menuId).size() >= maxButtons()) { error(player, "Batas button per menu tercapai: " + maxButtons()); showJavaMenu(player, holder.menuId, 0); return; }
            createButton(player, holder.menuId, key);
            showJavaButton(player, holder.menuId, key);
            return;
        }
        if (applyField(player, holder.menuId, holder.buttonKey, holder.field, raw)) {
            if (advancedField(holder.field)) showJavaAdvanced(player, holder.menuId, holder.buttonKey);
            else showJavaButton(player, holder.menuId, holder.buttonKey);
        } else {
            showJavaInput(player, holder.menuId, holder.buttonKey, holder.field);
        }
    }

    // ---------------- Bedrock Forms ----------------

    private void showBedrockRoot(Player player) {
        if (!allowed(player)) return;
        List<String> menus = menuIds();
        SimpleForm.Builder b = SimpleForm.builder().title("Admin Menu Editor").content("Pilih menu yang ingin diedit.");
        for (String id : menus) b.button(id + "\n" + buttonKeys(id).size() + " buttons");
        b.button("Tutup");
        send(player, b.validResultHandler(r -> sync(() -> {
            int i = r.clickedButtonId();
            if (i >= 0 && i < menus.size()) showBedrockMenu(player, menus.get(i));
        })).build());
    }

    private void showBedrockMenu(Player player, String menuId) {
        if (!allowed(player) || !menuExists(menuId)) { showBedrockRoot(player); return; }
        List<String> keys = buttonKeys(menuId);
        SimpleForm.Builder b = SimpleForm.builder().title("Menu • " + menuId).content("Kelola button langsung dari config.yml.");
        for (String key : keys) {
            String base = buttonPath(menuId,key);
            boolean enabled = plugin.getConfig().getBoolean(base + ".enabled", true);
            b.button((enabled ? "[ON] " : "[OFF] ") + key + "\n" + plugin.getConfig().getString(base + ".type", "command"));
        }
        b.button("+ Tambah Button");
        b.button("Kembali");
        send(player, b.validResultHandler(r -> sync(() -> {
            int i = r.clickedButtonId();
            if (i >= 0 && i < keys.size()) showBedrockButton(player, menuId, keys.get(i));
            else if (i == keys.size()) showBedrockInput(player, menuId, null, F_NEW_KEY);
            else if (i == keys.size()+1) showBedrockRoot(player);
        })).build());
    }

    private void showBedrockButton(Player player, String menuId, String key) {
        if (!allowed(player) || !buttonExists(menuId,key)) { showBedrockMenu(player,menuId); return; }
        String base=buttonPath(menuId,key);
        String content="Enabled: "+plugin.getConfig().getBoolean(base+".enabled",true)
                +"\nType: "+plugin.getConfig().getString(base+".type","command")
                +"\nName: "+plugin.getConfig().getString(base+".name",key)
                +"\nCommand: "+plugin.getConfig().getString(base+".command","")
                +"\nOrder: "+plugin.getConfig().getInt(base+".order",100);
        SimpleForm.Builder b=SimpleForm.builder().title("Button • "+key).content(content);
        b.button("Toggle Enabled"); b.button("Ganti Type"); b.button("Edit Name"); b.button("Edit Command");
        b.button("Edit Java Material"); b.button("Edit Bedrock Icon"); b.button("Edit Permission"); b.button("Edit Order");
        b.button("Edit Submenu"); b.button("Edit Lore"); b.button("Dependencies & Conditions"); b.button("Preview Menu");
        b.button("Hapus Button"); b.button("Kembali");
        send(player,b.validResultHandler(r->sync(()->{
            switch(r.clickedButtonId()){
                case 0->{toggleEnabled(player,menuId,key);showBedrockButton(player,menuId,key);} case 1->{cycleType(player,menuId,key);showBedrockButton(player,menuId,key);}
                case 2->showBedrockInput(player,menuId,key,F_NAME); case 3->showBedrockInput(player,menuId,key,F_COMMAND);
                case 4->showBedrockInput(player,menuId,key,F_MATERIAL); case 5->showBedrockInput(player,menuId,key,F_ICON);
                case 6->showBedrockInput(player,menuId,key,F_PERMISSION); case 7->showBedrockInput(player,menuId,key,F_ORDER);
                case 8->showBedrockInput(player,menuId,key,F_SUBMENU); case 9->showBedrockInput(player,menuId,key,F_LORE);
                case 10->showBedrockAdvanced(player,menuId,key); case 11->plugin.openMenu(player,menuId);
                case 12->showBedrockDelete(player,menuId,key); case 13->showBedrockMenu(player,menuId); default->{}
            }
        })).build());
    }

    private void showBedrockAdvanced(Player player,String menuId,String key){
        if(!allowed(player)||!buttonExists(menuId,key)){showBedrockMenu(player,menuId);return;}
        String base=buttonPath(menuId,key);
        SimpleForm.Builder b=SimpleForm.builder().title("Advanced • "+key).content("Platform: "+plugin.getConfig().getString(base+".conditions.platform","ANY"));
        b.button("Requires Command"); b.button("Requires Plugins"); b.button("Cycle Platform"); b.button("Worlds"); b.button("Excluded Worlds");
        b.button("Extra Permissions"); b.button("Min Online"); b.button("Max Online"); b.button("Kembali");
        send(player,b.validResultHandler(r->sync(()->{
            switch(r.clickedButtonId()){
                case 0->showBedrockInput(player,menuId,key,F_REQUIRES_COMMAND); case 1->showBedrockInput(player,menuId,key,F_REQUIRES_PLUGINS);
                case 2->{cyclePlatform(player,menuId,key);showBedrockAdvanced(player,menuId,key);} case 3->showBedrockInput(player,menuId,key,F_WORLDS);
                case 4->showBedrockInput(player,menuId,key,F_EXCLUDED_WORLDS); case 5->showBedrockInput(player,menuId,key,F_CONDITION_PERMISSIONS);
                case 6->showBedrockInput(player,menuId,key,F_MIN_ONLINE); case 7->showBedrockInput(player,menuId,key,F_MAX_ONLINE);
                case 8->showBedrockButton(player,menuId,key); default->{}
            }
        })).build());
    }

    private void showBedrockInput(Player player,String menuId,String key,String field){
        String initial=field.equals(F_NEW_KEY)?"":current(menuId,key,field);
        CustomForm form=CustomForm.builder().title("Edit • "+label(field))
                .input(label(field),inputHint(field)+" | '-' = kosong",initial)
                .closedOrInvalidResultHandler(()->sync(()->returnBedrock(player,menuId,key,field)))
                .validResultHandler(r->sync(()->{
                    String value=r.asInput(0); if(value==null)value="";
                    if(field.equals(F_NEW_KEY)){
                        String newKey=value.trim().toLowerCase(Locale.ROOT);
                        if(!KEY_PATTERN.matcher(newKey).matches()){error(player,"Key tidak valid.");showBedrockInput(player,menuId,null,F_NEW_KEY);return;}
                        if(buttonExists(menuId,newKey)){error(player,"Button key sudah ada.");showBedrockMenu(player,menuId);return;}
                        if(buttonKeys(menuId).size()>=maxButtons()){error(player,"Batas button per menu tercapai.");showBedrockMenu(player,menuId);return;}
                        createButton(player,menuId,newKey);showBedrockButton(player,menuId,newKey);return;
                    }
                    if(applyField(player,menuId,key,field,value)) returnBedrock(player,menuId,key,field); else showBedrockInput(player,menuId,key,field);
                })).build();
        send(player,form);
    }

    private void returnBedrock(Player player,String menuId,String key,String field){
        if(field.equals(F_NEW_KEY)){showBedrockMenu(player,menuId);return;}
        if(advancedField(field))showBedrockAdvanced(player,menuId,key);else showBedrockButton(player,menuId,key);
    }

    private void showBedrockDelete(Player player,String menuId,String key){
        ModalForm form=ModalForm.builder().title("Hapus Button").content("Hapus '"+key+"' dari menu '"+menuId+"'?")
                .button1("HAPUS").button2("BATAL").validResultHandler(r->sync(()->{
                    if(r.clickedFirst()){deleteButton(player,menuId,key);showBedrockMenu(player,menuId);}else showBedrockButton(player,menuId,key);
                })).build();
        send(player,form);
    }

    // ---------------- Mutations / validation ----------------

    private void toggleEnabled(Player player,String menuId,String key){
        String p=buttonPath(menuId,key)+".enabled";plugin.getConfig().set(p,!plugin.getConfig().getBoolean(p,true));save(player);
    }

    private void cycleType(Player player,String menuId,String key){
        String p=buttonPath(menuId,key)+".type";String current=plugin.getConfig().getString(p,"command");
        int i=TYPES.indexOf(current==null?"command":current.toLowerCase(Locale.ROOT));plugin.getConfig().set(p,TYPES.get((i+1+TYPES.size())%TYPES.size()));save(player);
    }

    private void cyclePlatform(Player player,String menuId,String key){
        String p=buttonPath(menuId,key)+".conditions.platform";String current=plugin.getConfig().getString(p,"ANY");
        int i=PLATFORMS.indexOf(current==null?"ANY":current.toUpperCase(Locale.ROOT));plugin.getConfig().set(p,PLATFORMS.get((i+1+PLATFORMS.size())%PLATFORMS.size()));save(player);
    }

    private void createButton(Player player,String menuId,String key){
        String base=buttonPath(menuId,key);plugin.getConfig().set(base+".enabled",true);plugin.getConfig().set(base+".name",key);
        plugin.getConfig().set(base+".type","command");plugin.getConfig().set(base+".command","");plugin.getConfig().set(base+".executor","player");
        plugin.getConfig().set(base+".order",nextOrder(menuId));plugin.getConfig().set(base+".icon","");plugin.getConfig().set(base+".java-material","PAPER");
        plugin.getConfig().set(base+".permission","");plugin.getConfig().set(base+".auto-detect-command",true);
        if(save(player)) player.sendMessage(Colors.legacy("&aButton &f"+key+" &aberhasil dibuat."));
    }

    private void deleteButton(Player player,String menuId,String key){
        plugin.getConfig().set(buttonPath(menuId,key),null);if(save(player))player.sendMessage(Colors.legacy("&aButton &f"+key+" &aberhasil dihapus."));
    }

    private boolean applyField(Player player,String menuId,String key,String field,String raw){
        if(!buttonExists(menuId,key)){error(player,"Button sudah tidak ada.");return false;}
        String value=raw==null?"":raw.trim();if(value.equals("-"))value="";
        String base=buttonPath(menuId,key);
        try{
            switch(field){
                case F_NAME->{if(value.isBlank()||value.length()>80){error(player,"Name wajib 1-80 karakter.");return false;}plugin.getConfig().set(base+".name",value);}
                case F_COMMAND->{if(value.length()>200){error(player,"Command maksimal 200 karakter.");return false;}plugin.getConfig().set(base+".command",value);}
                case F_MATERIAL->{if(value.isBlank()){plugin.getConfig().set(base+".java-material","PAPER");break;}Material m=Material.matchMaterial(value.toUpperCase(Locale.ROOT));if(m==null||m.isAir()||!m.isItem()){error(player,"Material Bukkit tidak valid: "+value);return false;}plugin.getConfig().set(base+".java-material",m.name());}
                case F_ICON->{if(value.length()>200){error(player,"Icon path maksimal 200 karakter.");return false;}plugin.getConfig().set(base+".icon",value);}
                case F_PERMISSION->{if(value.length()>160||value.contains(" ")){error(player,"Permission tidak valid / terlalu panjang.");return false;}plugin.getConfig().set(base+".permission",value);}
                case F_ORDER->{int n=Integer.parseInt(value);if(n < -100000 || n > 100000){error(player,"Order harus -100000 s/d 100000.");return false;}plugin.getConfig().set(base+".order",n);}
                case F_SUBMENU->{String v=value.toLowerCase(Locale.ROOT);if(!v.isBlank()&&!menuExists(v)){error(player,"Submenu tidak ditemukan: "+v);return false;}plugin.getConfig().set(base+".submenu",v);}
                case F_LORE->plugin.getConfig().set(base+".lore",splitPipe(value,20,120));
                case F_REQUIRES_COMMAND->{if(value.length()>120){error(player,"Requires command terlalu panjang.");return false;}plugin.getConfig().set(base+".requires-command",value);}
                case F_REQUIRES_PLUGINS->plugin.getConfig().set(base+".requires-plugins",splitComma(value,16,64));
                case F_WORLDS->plugin.getConfig().set(base+".conditions.worlds",splitComma(value,32,64));
                case F_EXCLUDED_WORLDS->plugin.getConfig().set(base+".conditions.excluded-worlds",splitComma(value,32,64));
                case F_CONDITION_PERMISSIONS->plugin.getConfig().set(base+".conditions.permissions",splitComma(value,32,160));
                case F_MIN_ONLINE->{int n=Integer.parseInt(value);if(n<0||n>100000){error(player,"Min online harus 0-100000.");return false;}plugin.getConfig().set(base+".conditions.min-online",n);}
                case F_MAX_ONLINE->{int n=Integer.parseInt(value);if(n < -1 || n > 100000){error(player,"Max online harus -1 atau 0-100000.");return false;}plugin.getConfig().set(base+".conditions.max-online",n);}
                default->{error(player,"Field editor tidak dikenal.");return false;}
            }
        }catch(NumberFormatException ex){error(player,"Nilai harus berupa angka.");return false;}
        return save(player);
    }

    private boolean save(Player player){
        try{plugin.saveConfig();plugin.menus().validateConfiguration();player.sendMessage(Colors.legacy("&aMenu config tersimpan."));return true;}
        catch(Throwable t){plugin.getLogger().severe("Admin Menu Editor save failed: "+t.getMessage());plugin.reloadConfig();error(player,"Gagal menyimpan config. Perubahan di-memory dibatalkan dengan reload.");return false;}
    }

    // ---------------- Data / UI helpers ----------------

    private List<String> menuIds(){List<String> out=new ArrayList<>();out.add("main");ConfigurationSection s=plugin.getConfig().getConfigurationSection("menu.submenus");if(s!=null)s.getKeys(false).stream().sorted(String.CASE_INSENSITIVE_ORDER).forEach(out::add);return out;}
    private boolean menuExists(String id){return id!=null&&plugin.getConfig().isConfigurationSection(menuPath(id));}
    private String menuPath(String id){return "main".equalsIgnoreCase(id)?"menu.main":"menu.submenus."+id.toLowerCase(Locale.ROOT);}
    private String buttonPath(String menuId,String key){return menuPath(menuId)+".buttons."+key;}
    private boolean buttonExists(String menuId,String key){return menuId!=null&&key!=null&&plugin.getConfig().isConfigurationSection(buttonPath(menuId,key));}
    private List<String> buttonKeys(String menuId){
        ConfigurationSection s=plugin.getConfig().getConfigurationSection(menuPath(menuId)+".buttons");if(s==null)return List.of();
        List<String> out=new ArrayList<>(s.getKeys(false));out.sort(Comparator.comparingInt((String k)->plugin.getConfig().getInt(buttonPath(menuId,k)+".order",100)).thenComparing(String.CASE_INSENSITIVE_ORDER));return out;
    }
    private int nextOrder(String menuId){return buttonKeys(menuId).stream().mapToInt(k->plugin.getConfig().getInt(buttonPath(menuId,k)+".order",100)).max().orElse(0)+10;}
    private int maxButtons(){return Math.max(1,Math.min(500,plugin.getConfig().getInt("admin-menu-editor.max-buttons-per-menu",100)));}
    private int clampPage(int p,int pages){return Math.max(0,Math.min(p,pages-1));}

    private String current(String menuId,String key,String field){
        if(field.equals(F_NEW_KEY))return "";String b=buttonPath(menuId,key);
        return switch(field){
            case F_NAME->plugin.getConfig().getString(b+".name",key);case F_COMMAND->plugin.getConfig().getString(b+".command","");
            case F_MATERIAL->plugin.getConfig().getString(b+".java-material","PAPER");case F_ICON->plugin.getConfig().getString(b+".icon","");
            case F_PERMISSION->plugin.getConfig().getString(b+".permission","");case F_ORDER->Integer.toString(plugin.getConfig().getInt(b+".order",100));
            case F_SUBMENU->plugin.getConfig().getString(b+".submenu","");case F_LORE->String.join(" | ",plugin.getConfig().getStringList(b+".lore"));
            case F_REQUIRES_COMMAND->plugin.getConfig().getString(b+".requires-command","");case F_REQUIRES_PLUGINS->String.join(",",plugin.getConfig().getStringList(b+".requires-plugins"));
            case F_WORLDS->String.join(",",plugin.getConfig().getStringList(b+".conditions.worlds"));case F_EXCLUDED_WORLDS->String.join(",",plugin.getConfig().getStringList(b+".conditions.excluded-worlds"));
            case F_CONDITION_PERMISSIONS->String.join(",",plugin.getConfig().getStringList(b+".conditions.permissions"));case F_MIN_ONLINE->Integer.toString(plugin.getConfig().getInt(b+".conditions.min-online",0));
            case F_MAX_ONLINE->Integer.toString(plugin.getConfig().getInt(b+".conditions.max-online",-1));default->"";};
    }

    private boolean advancedField(String f){return Set.of(F_REQUIRES_COMMAND,F_REQUIRES_PLUGINS,F_WORLDS,F_EXCLUDED_WORLDS,F_CONDITION_PERMISSIONS,F_MIN_ONLINE,F_MAX_ONLINE).contains(f);}
    private String label(String f){return switch(f){case F_NEW_KEY->"Button Key";case F_NAME->"Name";case F_COMMAND->"Command";case F_MATERIAL->"Java Material";case F_ICON->"Bedrock Icon";case F_PERMISSION->"Permission";case F_ORDER->"Order";case F_SUBMENU->"Submenu";case F_LORE->"Lore";case F_REQUIRES_COMMAND->"Requires Command";case F_REQUIRES_PLUGINS->"Requires Plugins";case F_WORLDS->"Worlds";case F_EXCLUDED_WORLDS->"Excluded Worlds";case F_CONDITION_PERMISSIONS->"Condition Permissions";case F_MIN_ONLINE->"Min Online";case F_MAX_ONLINE->"Max Online";default->f;};}
    private String placeholder(String f){return switch(f){case F_NEW_KEY->"contoh: bank";case F_ORDER,F_MIN_ONLINE->"0";case F_MAX_ONLINE->"-1";case F_MATERIAL->"PAPER";default->"Ketik nilai...";};}
    private String inputHint(String f){return switch(f){case F_NEW_KEY->"a-z, 0-9, _ dan -";case F_LORE->"Pisahkan baris dengan karakter |";case F_REQUIRES_PLUGINS,F_WORLDS,F_EXCLUDED_WORLDS,F_CONDITION_PERMISSIONS->"Pisahkan beberapa nilai dengan koma";case F_SUBMENU->"Harus ID submenu yang sudah ada";default->"Masukkan nilai baru";};}
    private List<String> splitComma(String raw,int max,int each){return split(raw,",",max,each);}
    private List<String> splitPipe(String raw,int max,int each){return split(raw,"\\|",max,each);}
    private List<String> split(String raw,String regex,int max,int each){if(raw==null||raw.isBlank())return List.of();List<String> out=new ArrayList<>();for(String p:raw.split(regex)){String v=p.trim();if(v.isBlank())continue;if(v.length()>each)v=v.substring(0,each);out.add(v);if(out.size()>=max)break;}return List.copyOf(out);}

    private ItemStack buttonInfo(String menuId,String key){String b=buttonPath(menuId,key);return item(Material.WRITTEN_BOOK,"&d&l"+key,List.of("&7Name: &f"+safe(plugin.getConfig().getString(b+".name",key)),"&7Type: &f"+safe(plugin.getConfig().getString(b+".type","command")),"&7Enabled: &f"+plugin.getConfig().getBoolean(b+".enabled",true),"&7Order: &f"+plugin.getConfig().getInt(b+".order",100)));}
    private ItemStack fieldItem(Material m,String title,String field,String value){return actionItem(m,title,FIELD_PREFIX+field,List.of("&7Current: &f"+shorten(value==null||value.isBlank()?"(kosong)":value,48),"","&8» &fKlik untuk edit."));}
    private ItemStack actionItem(Material m,String name,String action,List<String> lore){ItemStack it=item(m,name,lore);ItemMeta meta=it.getItemMeta();meta.getPersistentDataContainer().set(plugin.buttonKey(),PersistentDataType.STRING,action);it.setItemMeta(meta);return it;}
    private ItemStack item(Material m,String name,List<String> lore){ItemStack it=new ItemStack(m);ItemMeta meta=it.getItemMeta();meta.setDisplayName(Colors.legacy(name));if(lore!=null&&!lore.isEmpty())meta.setLore(lore.stream().map(Colors::legacy).toList());it.setItemMeta(meta);return it;}
    private String action(ItemStack it){if(it==null||!it.hasItemMeta())return null;return it.getItemMeta().getPersistentDataContainer().get(plugin.buttonKey(),PersistentDataType.STRING);}
    private ItemStack filler(){return item(Material.BLACK_STAINED_GLASS_PANE," ",List.of());}
    private void fill(Inventory inv,ItemStack item){for(int i=0;i<inv.getSize();i++)inv.setItem(i,item.clone());}
    private void decorate(Inventory inv){fill(inv,filler());for(int i=0;i<9&&i<inv.getSize();i++)inv.setItem(i,item(Material.MAGENTA_STAINED_GLASS_PANE," ",List.of()));}
    private String trim(String s){return s.length()<=32?s:s.substring(0,32);}
    private String shorten(String s,int max){if(s==null)return"";return s.length()<=max?s:s.substring(0,Math.max(0,max-3))+"...";}
    private String safe(String s){return s==null?"":s;}
    private void error(Player p,String msg){p.sendMessage(Colors.legacy("&c[Menu Editor] &f"+msg));}

    private void send(Player player, Form form){FloodgateApi.getInstance().sendForm(player.getUniqueId(),form);}
    private void sync(Runnable r){Bukkit.getScheduler().runTask(plugin,r);}

    private enum View{ROOT,MENU,BUTTON,ADVANCED,INPUT,DELETE_CONFIRM}

    private static final class EditorHolder implements InventoryHolder{
        private final View view;private final String menuId;private final String buttonKey;private final String field;private final int page;private final Inventory inventory;
        private EditorHolder(View view,String menuId,String buttonKey,String field,int page,int size,String title){this.view=view;this.menuId=menuId;this.buttonKey=buttonKey;this.field=field;this.page=Math.max(0,page);this.inventory=Bukkit.createInventory(this,size,title);}
        private EditorHolder(View view,String menuId,String buttonKey,String field,int page,InventoryType type,String title){this.view=view;this.menuId=menuId;this.buttonKey=buttonKey;this.field=field;this.page=Math.max(0,page);this.inventory=Bukkit.createInventory(this,type,title);}
        @Override public @NotNull Inventory getInventory(){return inventory;}
    }
}
