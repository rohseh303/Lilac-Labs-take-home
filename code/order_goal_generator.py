import random
from menu_manager import MenuManager

class OrderGoalGenerator:
    def __init__(self):
        self.menu_manager = MenuManager()

    def generate_simple_order(self):
        """Generate a simple order with minimal customization."""
        items = self.menu_manager.get_all_items()
        # item_def = random.choice(items)
        item_def = next(item for item in items if item["itemName"] == "Classic Hot Dog")

        # Always fill required options
        required_keys, required_values = self._pick_required_options(item_def)

        # Possibly skip optional
        optional_keys, optional_values = [], []

        return [{
            "itemName": item_def["itemName"],
            "optionKeys": required_keys + optional_keys,
            "optionValues": required_values + optional_values
        }]

    def generate_medium_order(self):
        """Generate a medium complexity order with 2–3 items."""
        all_items = self.menu_manager.get_all_items()
        num_items = random.randint(2, 3)

        order_items = []
        for _ in range(num_items):
            item_def = random.choice(all_items)
            required_keys, required_values = self._pick_required_options(item_def)
            # randomly pick optional options
            opt_keys, opt_values = self._pick_optional_options(item_def)
            order_items.append({
                "itemName": item_def["itemName"],
                "optionKeys": required_keys + opt_keys,
                "optionValues": required_values + opt_values
            })

        return order_items

    def generate_complex_order(self):
        """Generate a complex order with multiple items & customizations."""
        all_items = self.menu_manager.get_all_items()
        num_items = random.randint(3, 5)

        order_items = []
        for _ in range(num_items):
            item_def = random.choice(all_items)
            required_keys, required_values = self._pick_required_options(item_def)
            opt_keys, opt_values = self._pick_optional_options(item_def)
            order_items.append({
                "itemName": item_def["itemName"],
                "optionKeys": required_keys + opt_keys,
                "optionValues": required_values + opt_values
            })

        return order_items

    def _pick_required_options(self, item_def):
        """Pick required options based on the menu item definition."""
        keys = []
        values = []
        
        # Get all options from the item definition
        options = item_def.get("options", {})
        
        # Iterate through each option category
        for opt_name, opt_def in options.items():
            # Check if option is required
            is_required = opt_def.get("required", False)
            
            # Handle both boolean and conditional requirements
            if isinstance(is_required, dict):
                # This is a conditional requirement (e.g., side options for meals)
                # We'd need to check against previously selected values
                continue  # For now, skip conditional requirements
                
            elif is_required:
                keys.append(opt_name)
                
                # Get the choices available
                choices = opt_def.get("choices", {})
                
                # Check if there's a default choice specified
                default = opt_def.get("defaultChoice")
                
                # Special handling for customizations
                if opt_name == "customizations":
                    modifiers = opt_def.get("modifiers", [""])
                    min_selections = opt_def.get("minimum", 1)
                    max_selections = opt_def.get("maximum", 1)
                    num_selections = random.randint(min_selections, max_selections)
                    
                    selected_items = random.sample(list(choices.keys()), num_selections)
                    # Add random modifier to each selected item
                    selected_with_modifiers = [f"{random.choice(modifiers)} {item}" for item in selected_items]
                    values.append(selected_with_modifiers)
                else:
                    if default and default in choices:
                        values.append([default])
                    else:
                        # Pick a random choice respecting minimum/maximum constraints
                        min_selections = opt_def.get("minimum", 1)
                        max_selections = opt_def.get("maximum", 1)
                        num_selections = random.randint(min_selections, max_selections)
                        
                        selected = random.sample(list(choices.keys()), num_selections)
                        values.append(selected)
        
        return keys, values

    def _pick_optional_options(self, item_def):
        """Randomly pick zero or more optional option values."""
        keys = []
        values = []
        for o_opt in item_def.get("optionalOptions", []):
            # 50% chance to add an optional option
            if random.random() < 0.5:
                keys.append(o_opt["key"])
                # 1-2 random picks from possibleValues
                possible_vals = random.sample(
                    o_opt["possibleValues"],
                    k=random.randint(1, min(2, len(o_opt["possibleValues"])))
                )
                values.append(possible_vals)
        return keys, values
