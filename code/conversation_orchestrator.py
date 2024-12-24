import random

class ConversationOrchestrator:
    def __init__(self, lilac_client):
        self.lilac_client = lilac_client

    def run_conversation(self, order_id, order_goal):
        """
        Simulate a conversation that attempts to fulfill the 'order_goal'.
        Each item in 'order_goal' is added through user messages.
        Potentially ask for modifications, etc.
        """
        messages_log = []
        
        # Start greeting from Lilac's agent (simulate we got a greeting back)
        greet_response = self.lilac_client.send_chat_message(order_id, "Hi!")
        messages_log.append({
            "role": "assistant", 
            "content": greet_response["messages"][-1]["content"] if greet_response["messages"] else "Hello!"
        })

        # For each item in our goal, build the conversation.
        for idx, item in enumerate(order_goal):
            # Example message: "I want a Classic Hot Dog with no onions"
            # We'll do a simplified approach:
            user_msg = self._construct_user_message_for_item(item)
            step_response = self.lilac_client.send_chat_message(order_id, user_msg)
            messages_log.append({"role": "user", "content": user_msg})
            messages_log.append({"role": "assistant", "content": step_response["messages"][-1]["content"]})

            # After each step, we can retrieve the current order to see if it matches expectation
            current_order = step_response["order"]
            # If we see a mismatch, we might correct it. This is the "bonus" scenario.
            self._maybe_correct_order(order_id, current_order, item, messages_log)

        # Now finalize
        finalize_msg = "No more items"
        finalize_resp = self.lilac_client.send_chat_message(order_id, finalize_msg)
        messages_log.append({"role": "user", "content": finalize_msg})
        messages_log.append({"role": "assistant", "content": finalize_resp["messages"][-1]["content"]})

        return messages_log

    # make actual customer dynamic convo, like a real person would order
    def _construct_user_message_for_item(self, item):
        print("what goal looks like: ",item)
        # Example approach: Use itemName and its first required or optional option
        # A more advanced approach could craft more natural language.
        item_name = item["itemName"]
        # Flatten the user’s textual desire:
        # e.g. "classic hot dog with no onions, meal with regular fries and coke"
        
        # We'll just join them, but you can do more creative prompts
        all_options_text = []
        for k, v in zip(item["optionKeys"], item["optionValues"]):
            if len(v) > 0:
                # Option might be "customizations: ['no onions']"
                joined = " and ".join(v)
                all_options_text.append(f"{k}={joined}")
        options_str = ", ".join(all_options_text)

        # naive approach
        return f"I would like a {item_name} with {options_str}" if options_str else f"I would like a {item_name}"

    def _maybe_correct_order(self, order_id, current_order, desired_item, messages_log):
        """
        Compare the last item in current_order with desired_item.
        If there's a mismatch, send a correction message.
        """
        if not current_order:
            return
        last_added = current_order[-1]
        # Very naive approach: compare itemName only
        if last_added["itemName"].lower() != desired_item["itemName"].lower():
            # Send correction
            correction_message = f"Sorry, I meant to order {desired_item['itemName']} instead of {last_added['itemName']}"
            correction_resp = self.lilac_client.send_chat_message(order_id, correction_message)
            messages_log.append({"role": "user", "content": correction_message})
            messages_log.append({"role": "assistant", "content": correction_resp["messages"][-1]["content"]})
