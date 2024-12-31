import random
from menu_manager import MenuManager

class OrderGoalGenerator:
    def __init__(self):
        self.menu_manager = MenuManager()

    def generate_simple_order(self):
        """Generate a simple order with minimal customization."""
        items = self.menu_manager.get_all_items()
        item_def = random.choice(items)
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
        # Filter for items that can be meals
        items = [item for item in self.menu_manager.get_all_items() if item.get("itemType") == "main - meal option"]
        
        item_def = random.choice(items)
        required_keys, required_values = self._pick_required_options(item_def, meal_mode=True)

        return [{
            "itemName": item_def["itemName"],
            "optionKeys": required_keys,
            "optionValues": required_values
        }]

    def generate_complex_order(self):
        """Generate a complex order with multiple items & customizations."""
        # Get all items and meal items
        all_items = self.menu_manager.get_all_items()
        meal_items = [item for item in all_items if item.get("itemType") == "main - meal option"]
        
        num_items = random.randint(2, 3)
        order_items = []

        # First, add one meal item
        meal_item = random.choice(meal_items)
        required_keys, required_values = self._pick_required_options(meal_item, meal_mode=True)
        order_items.append({
            "itemName": meal_item["itemName"],
            "optionKeys": required_keys,
            "optionValues": required_values
        })

        # Then add remaining random items
        for _ in range(num_items - 1):
            item_def = random.choice(all_items)
            required_keys, required_values = self._pick_required_options(item_def)
            order_items.append({
                "itemName": item_def["itemName"],
                "optionKeys": required_keys,
                "optionValues": required_values
            })

        return order_items

    def _pick_required_options(self, item_def, simple_mode=False, meal_mode=False): #alter the mode to string type
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
            
            if is_required: # reorder to handle string type for simple type vs medium type
                keys.append(opt_name)
                # In simple mode, always choose 'a la carte' for meal options
                if simple_mode and opt_name == "meal option":
                    values.append(["a la carte"])
                    selected_values[opt_name] = "a la carte"
                elif meal_mode and opt_name == "meal option":
                    values.append(["meal"])
                    selected_values[opt_name] = "meal"
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
