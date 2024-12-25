from constants import MENU_JSON

class MenuManager:
    def __init__(self):
        self.menu = MENU_JSON

    def get_all_items(self):
        """Return a list of all item definitions from the menu."""
        return self.menu

    def find_item_definition(self, item_name):
        """Return the item definition for a given item name."""
        for item_def in self.menu:
            if item_def["itemName"].lower() == item_name.lower():
                return item_def
        return None
