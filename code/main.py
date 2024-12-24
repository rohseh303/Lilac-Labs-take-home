from lilac_api_client import LilacApiClient
from order_goal_generator import OrderGoalGenerator
from conversation_orchestrator import ConversationOrchestrator

def run_simulation(order_complexity="simple"):
    """
    Run the entire pipeline:
    1. Generate an order goal (simple, medium, or complex)
    2. Start a new order
    3. Simulate the conversation
    4. Print out final conversation logs and final order
    """
    # Step 1: Generate the order goal
    generator = OrderGoalGenerator()
    if order_complexity == "simple":
        goal = generator.generate_simple_order()
    elif order_complexity == "medium":
        goal = generator.generate_medium_order()
    else:
        goal = generator.generate_complex_order()

    # Step 2: Start a new order
    lilac_client = LilacApiClient()
    order_id = lilac_client.start_order()

    # Step 3: Simulate conversation
    orchestrator = ConversationOrchestrator(lilac_client)
    conversation_log = orchestrator.run_conversation(order_id, goal)

    # Retrieve final order
    final_state = lilac_client.retrieve_order(order_id)
    final_order = final_state["order"]

    # Step 4: Print or log results
    print("\n==========================")
    print(" Conversation Transcript ")
    print("==========================\n")
    for msg in conversation_log:
        print(f"{msg['role'].upper()}: {msg['content']}")

    print("\n==========================")
    print(" Final Order Returned ")
    print("==========================\n")
    for item in final_order:
        print({
            "itemName": item["itemName"],
            "optionKeys": item["optionKeys"],
            "optionValues": item["optionValues"],
        })

    # Add order comparison
    print("\n==========================")
    print(" Order Verification ")
    print("==========================\n")
    
    def compare_orders(goal_order, final_order):
        if len(goal_order) != len(final_order):
            print(f"❌ Order length mismatch: Goal has {len(goal_order)} items, Final has {len(final_order)} items")
            return False
        
        for i, (goal_item, final_item) in enumerate(zip(goal_order, final_order)):
            if goal_item != final_item:
                print(f"\nDifference in item {i + 1}:")
                for key in ['itemName', 'optionKeys', 'optionValues']:
                    if goal_item.get(key) != final_item.get(key):
                        print(f"❌ {key}:")
                        print(f"  Goal:  {goal_item.get(key)}")
                        print(f"  Final: {final_item.get(key)}")
                        return False
        
        return True

    orders_match = compare_orders(goal, final_order)
    if orders_match:
        print("✅ Goal order matches final order exactly!")

if __name__ == "__main__":
    # Example usage
    run_simulation(order_complexity="simple")
    # run_simulation(order_complexity="medium")
    # run_simulation(order_complexity="complex")
