package id.cadera.memberbook.menu;

import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import id.cadera.memberbook.CdrMemberBookPlugin;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class MenuConfigService {
    private static final Set<String> KNOWN_TYPES = Set.of("command", "teleport", "homes", "pay", "trade", "report", "submenu", "close");
    private static final Set<String> ACTION_TYPES = Set.of("command", "console-command", "message", "sound", "close", "open-menu", "delay");
    private final CdrMemberBookPlugin plugin;
    public MenuConfigService(CdrMemberBookPlugin plugin) { this.plugin = plugin; }

    public MenuDefinition getMenu(String menuId) {
        String normalized = normalizeMenuId(menuId);
        String path = normalized.equals("main") ? "menu.main" : "menu.submenus." + normalized;
        ConfigurationSection section = plugin.getConfig().getConfigurationSection(path);
        if (section == null) return null;
        String title = section.getString("title", normalized.equals("main") ? "CdrMemberBook • Menu Member" : normalized);
        String content = section.getString("content", "");
        String backMenu = normalizeMenuId(section.getString("back-menu", "main"));
        List<MenuButton> buttons = new ArrayList<>();
        ConfigurationSection bs = section.getConfigurationSection("buttons");
        if (bs != null) for (String key : bs.getKeys(false)) {
            ConfigurationSection b = bs.getConfigurationSection(key);
            if (b == null || !b.getBoolean("enabled", true)) continue;
            String type = b.getString("type", "command"); if (type == null) type = "command";
            buttons.add(new MenuButton(key, b.getString("name", key), type.trim().toLowerCase(Locale.ROOT),
                    b.getString("command", ""), b.getString("executor", "player"), b.getString("submenu", ""),
                    b.getString("icon", ""), b.getString("java-material", "PAPER"), b.getString("permission", ""),
                    b.getInt("order", 100), b.getStringList("lore"), b.getStringList("requires-plugins"),
                    b.getString("requires-command", ""), b.getBoolean("auto-detect-command", true), parseActions(b)));
        }
        buttons.sort(Comparator.comparingInt(MenuButton::order).thenComparing(MenuButton::key));
        return new MenuDefinition(normalized, title == null ? "" : title, content == null ? "" : content, backMenu, List.copyOf(buttons));
    }

    private List<MenuAction> parseActions(ConfigurationSection button) {
        List<MenuAction> actions = new ArrayList<>();
        for (Map<?, ?> raw : button.getMapList("actions")) {
            String type = string(raw.get("type"), "").trim().toLowerCase(Locale.ROOT);
            if (type.isBlank()) continue;
            String value = string(raw.get("value"), "");
            if (value.isBlank()) {
                for (String key : List.of("command", "message", "sound", "menu")) if (raw.get(key) != null) { value = raw.get(key).toString(); break; }
            }
            actions.add(new MenuAction(type, value, string(raw.get("executor"), "player"), number(raw.get("ticks"), 1L),
                    decimal(raw.get("volume"), 1.0f), decimal(raw.get("pitch"), 1.0f)));
        }
        return List.copyOf(actions);
    }
    private String string(Object value, String fallback) { return value == null ? fallback : value.toString(); }
    private long number(Object value, long fallback) { try { return value == null ? fallback : Long.parseLong(value.toString()); } catch (NumberFormatException e) { return fallback; } }
    private float decimal(Object value, float fallback) { try { return value == null ? fallback : Float.parseFloat(value.toString()); } catch (NumberFormatException e) { return fallback; } }

    public List<MenuButton> visibleButtons(MenuDefinition menu, Player player) {
        boolean hidePerm = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);
        return menu.buttons().stream().filter(b -> !hidePerm || canUse(player,b)).filter(b -> !hideUnavailable || availability(player,b).available()).toList();
    }
    public boolean canUse(Player player, MenuButton button) { String p=button.permission(); return p==null || p.isBlank() || player.hasPermission(p); }
    public boolean isAvailable(Player player, MenuButton button) { return availability(player,button).available(); }

    public Availability availability(Player player, MenuButton button) {
        for (String p : button.requiredPlugins()) if (p != null && !p.isBlank() && !plugin.getServer().getPluginManager().isPluginEnabled(p.trim())) return new Availability(false,"missing-plugin",p.trim());
        if (button.requiredCommand()!=null && !button.requiredCommand().isBlank() && !commandAvailable(button.requiredCommand())) return new Availability(false,"missing-command",rootCommand(button.requiredCommand()));
        if (!button.actions().isEmpty()) return actionsAvailability(button.actions());
        if (!KNOWN_TYPES.contains(button.type())) return new Availability(false,"invalid-type","type="+button.type());
        return switch(button.type()) {
            case "teleport","close" -> new Availability(true,"ok","built-in");
            case "submenu" -> button.submenu()==null || button.submenu().isBlank() || getMenu(button.submenu())==null ? new Availability(false,"missing-submenu",button.submenu()==null?"":button.submenu()) : new Availability(true,"ok","submenu="+button.submenu());
            case "homes" -> plugin.homes()!=null && plugin.homes().available() ? new Availability(true,"ok","EssentialsX") : new Availability(false,"missing-integration","EssentialsX Home");
            case "pay" -> availableCommand(plugin.getConfig().getString("integrations.pay.command","pay %target% %amount%"));
            case "trade" -> !plugin.getServer().getPluginManager().isPluginEnabled("AxTrade") ? new Availability(false,"missing-plugin","AxTrade") : availableCommand(plugin.getConfig().getString("integrations.axtrade.send-command","axtrade %target%"));
            case "report" -> (plugin.reports()!=null && plugin.reports().enabled() && plugin.forms()!=null && plugin.forms().isBedrock(player)) ? new Availability(true,"ok","native-report") : availableCommand(button.command());
            case "command" -> button.command()==null || button.command().isBlank() ? new Availability(false,"empty-command","command kosong") : (!plugin.getConfig().getBoolean("menu.auto-detect-command-dependencies",true) || !button.autoDetectCommand() ? new Availability(true,"ok","auto-detect off") : availableCommand(button.command()));
            default -> new Availability(false,"invalid-type",button.type());
        };
    }

    private Availability actionsAvailability(List<MenuAction> actions) {
        for (MenuAction action : actions) {
            if (!ACTION_TYPES.contains(action.type())) return new Availability(false,"invalid-action","action="+action.type());
            if ((action.type().equals("command") || action.type().equals("console-command")) && plugin.getConfig().getBoolean("menu.auto-detect-command-dependencies",true) && !commandAvailable(action.value())) return new Availability(false,"missing-command",rootCommand(action.value()));
            if (action.type().equals("open-menu") && getMenu(action.value()) == null) return new Availability(false,"missing-submenu",action.value());
            if (action.type().equals("sound")) try { org.bukkit.Sound.valueOf(action.value().trim().toUpperCase(Locale.ROOT)); } catch (Exception e) { return new Availability(false,"invalid-sound",action.value()); }
        }
        return new Availability(true,"ok","actions="+actions.size());
    }
    private Availability availableCommand(String c) { return commandAvailable(c) ? new Availability(true,"ok","command="+rootCommand(c)) : new Availability(false,"missing-command",rootCommand(c)); }

    public void validateConfiguration() {
        if (!plugin.getConfig().getBoolean("menu.log-invalid-buttons",true)) return;
        List<String> ids=new ArrayList<>(); ids.add("main"); ConfigurationSection sec=plugin.getConfig().getConfigurationSection("menu.submenus"); if(sec!=null) ids.addAll(sec.getKeys(false));
        for(String id:ids){ MenuDefinition menu=getMenu(id); if(menu==null)continue; for(MenuButton b:menu.buttons()){
            if(b.actions().isEmpty() && !KNOWN_TYPES.contains(b.type())) warn(id,b.key(),"type tidak dikenal: "+b.type());
            if(b.actions().isEmpty() && b.type().equals("command") && (b.command()==null||b.command().isBlank())) warn(id,b.key(),"command kosong");
            if(b.javaMaterial()!=null && Material.matchMaterial(b.javaMaterial())==null) warn(id,b.key(),"java-material tidak valid: "+b.javaMaterial());
            for(MenuAction a:b.actions()) if(!ACTION_TYPES.contains(a.type())) warn(id,b.key(),"action tidak dikenal: "+a.type());
        }}
    }
    private void warn(String m,String b,String r){ plugin.getLogger().warning("Menu config ["+m+"/"+b+"]: "+r); }
    public boolean commandAvailable(String template){String r=rootCommand(template);return !r.isBlank()&&plugin.getServer().getCommandMap().getCommand(r.toLowerCase(Locale.ROOT))!=null;}
    public String rootCommand(String template){if(template==null||template.isBlank())return"";String n=template.trim();if(n.startsWith("/"))n=n.substring(1);int sp=n.indexOf(' ');String r=sp<0?n:n.substring(0,sp);return r.contains("%")?"":r;}
    public MenuButton findButton(MenuDefinition m,String k){if(k==null)return null;for(MenuButton b:m.buttons())if(b.key().equals(k))return b;return null;}
    public String normalizeMenuId(String id){return id==null||id.isBlank()?"main":id.trim().toLowerCase(Locale.ROOT);}

    public record Availability(boolean available,String code,String detail){}
    public record MenuAction(String type,String value,String executor,long ticks,float volume,float pitch){}
    public record MenuDefinition(String id,String title,String content,String backMenu,List<MenuButton> buttons){}
    public record MenuButton(String key,String name,String type,String command,String executor,String submenu,String icon,String javaMaterial,String permission,int order,List<String> lore,List<String> requiredPlugins,String requiredCommand,boolean autoDetectCommand,List<MenuAction> actions){}
}
