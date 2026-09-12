from pathlib import Path

p = Path('src/main/java/id/cadera/memberbook/item/MemberBookService.java')
s = p.read_text()
old = '''    public void onInventoryClick(InventoryClickEvent event) {
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
'''
new = '''    public void onInventoryClick(InventoryClickEvent event) {
        if (!(event.getWhoClicked() instanceof Player player)) return;
        if (!isEligibleForBook(player)) return;

        boolean externalProtection = preventExternalStorage();
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

        if (!externalProtection) {
            if (touchedBook) scheduleRepair(player);
            return;
        }

        if (cursorBook && clickedForeignInventory) {
'''
if old not in s:
    raise SystemExit('locked guard pattern not found')
p.write_text(s.replace(old, new, 1))
print('v1.6.0 locked inventory guard fixed')
