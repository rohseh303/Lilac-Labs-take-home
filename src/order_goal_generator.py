import random
from menu_manager import MenuManager

class OrderGoalGenerator:
    def __init__(self):
        self.menu_manager = MenuManager()

    def generate_simple_order(self):
        """Generate a simple order with minimal customization."""
        items = self.menu_manager.get_all_items()
        item_def = random.choice(items)
        # item_def = next(item for item in items if item["itemName"] == "Polish Sausage Dog")

        required_keys, required_values = self._pick_required_options(item_def, simple_mode=True)
        optional_keys, optional_values = [], []

        return [{
            "itemName": item_def["itemName"],
            "optionKeys": required_keys + optional_keys,
            "optionValues": required_values + optional_values
        }]

    def generate_medium_order(self):
        """Generate a medium complexity order with an item with a lot of options."""
        print("Generating medium order")
        items = self.menu_manager.get_all_items()

        item_def = random.choice(items)
        # item_def = next(item for item in items if item["itemName"] == "Plain Classic Hot Dog")

        required_keys, required_values = self._pick_required_options(item_def, simple_mode=False)

        return [{
            "itemName": item_def["itemName"],
            "optionKeys": required_keys,
            "optionValues": required_values
        }]

    def generate_complex_order(self):
        """Generate a complex order with multiple items & customizations."""
        items = self.menu_manager.get_all_items()
        num_items = random.randint(2, 3)

        order_items = []
        for _ in range(num_items):
            item_def = random.choice(items)
            required_keys, required_values = self._pick_required_options(item_def)
            order_items.append({
                "itemName": item_def["itemName"],
                "optionKeys": required_keys,
                "optionValues": required_values
            })

        return order_items

    def _pick_required_options(self, item_def, simple_mode=False):
        """Pick required options based on the menu item definition."""
        keys = []
        values = []
        selected_values = {} 
        
        # Get all options from the item definition
        options = item_def.get("options", {})

        # First pass: handle unconditionally required options
        for opt_name, opt_def in options.items():
            is_required = opt_def.get("required", False)
            
            # Skip conditional requirements in first pass
            if isinstance(is_required, dict):
                continue
            
            if is_required:
                keys.append(opt_name)
                # In simple mode, always choose 'a la carte' for meal options
                if simple_mode and opt_name == "meal option":
                    values.append(["a la carte"])
                    selected_values[opt_name] = "a la carte"
                else:
                    selected_value = self._pick_option_value(opt_name, opt_def, simple_mode)
                    values.append(selected_value)
                    if selected_value:
                        selected_values[opt_name] = selected_value[0]   
            # do optional values here
            elif not simple_mode and not is_required:
                keys.append(opt_name)
                selected_value = self._pick_option_value(opt_name, opt_def, simple_mode)
                values.append(selected_value)
                if selected_value:
                    selected_values[opt_name] = selected_value[0]
        
        # Skip conditional requirements in simple mode
        if not simple_mode:
            # Second pass: handle conditional requirements
            for opt_name, opt_def in options.items():
                is_required = opt_def.get("required", False)
                
                if isinstance(is_required, dict):
                    # Check if condition is met
                    condition_option = is_required.get("option")
                    condition_value = is_required.get("value")
                    
                    if (condition_option in selected_values and 
                        selected_values[condition_option] == condition_value):
                        keys.append(opt_name)
                        selected_value = self._pick_option_value(opt_name, opt_def, simple_mode)
                        values.append(selected_value)
        
        return keys, values

    def _pick_option_value(self, opt_name, opt_def, simple_mode=False):
        """Helper method to pick appropriate values for an option."""
        choices = opt_def.get("choices", {})
        default = opt_def.get("defaultChoice")
        min_selections = opt_def.get("minimum", 1)
        
        # In simple mode, return empty list if minimum selections can be 0
        if simple_mode and min_selections == 0:
            return []
        
        # Special handling for customizations
        if opt_name == "customizations":
            modifiers = opt_def.get("modifiers", [""])
            max_selections = min(opt_def.get("maximum", 1), 4)  # Limit to 3 selections
            num_selections = random.randint(min_selections, max_selections)
            
            selected_items = random.sample(list(choices.keys()), num_selections)
            selected_with_modifiers = [f"{random.choice(modifiers)} {item}" for item in selected_items]
            return selected_with_modifiers
        
        # Handle regular options
        if simple_mode and default and default in choices:
            return [default]
        else:
            max_selections = min(opt_def.get("maximum", 1), 4)  # Limit to 4 selections
            num_selections = random.randint(min_selections, max_selections)
            
            return random.sample(list(choices.keys()), num_selections)
