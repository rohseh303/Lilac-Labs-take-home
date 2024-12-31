from lilac_api_client import LilacApiClient
from order_goal_generator import OrderGoalGenerator
from conversation_orchestrator import ConversationOrchestrator
import threading
import time
from queue import Queue
import concurrent.futures
import copy

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

    print(f"Running simulation with: {goal}")
    # Step 2: Start a new order
    lilac_client = LilacApiClient()
    order_id = lilac_client.start_order()

    # Step 3: Simulate conversation
    orchestrator = ConversationOrchestrator(lilac_client)
    goal_copy = copy.deepcopy(goal)
    conversation_log = orchestrator.run_conversation(order_id, goal_copy)

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
    
    orders_match = compare_orders(goal, final_order)
    if orders_match:
        print("✅ Goal order matches final order exactly!")

    print("\nExpected Goal Order:")
    for item in goal:
        print({
            "itemName": item["itemName"],
            "optionKeys": item["optionKeys"],
            "optionValues": item["optionValues"],
        })
    
    return orders_match

def compare_orders(goal_order, final_order):
    if len(goal_order) != len(final_order):
        print(f"❌ Order length mismatch: Goal has {len(goal_order)} items, Final has {len(final_order)} items")
        return False
    
    for i, (goal_item, final_item) in enumerate(zip(goal_order, final_order)):
        # Compare itemName directly
        if goal_item['itemName'] != final_item['itemName']:
            print(f"\nDifference in item {i + 1}:")
            print(f"❌ itemName:")
            print(f"  Goal:  {goal_item['itemName']}")
            print(f"  Final: {final_item['itemName']}")
            return False
        
        # Filter out keys with empty values from both items
        goal_keys_values = []
        final_keys_values = []
        
        for k, v in zip(goal_item['optionKeys'], goal_item['optionValues']):
            if v:
                # If v is a list, sort it using custom key function
                if isinstance(v, list):
                    v = sorted(v, key=lambda x: x.split()[-1] if len(x.split()) > 1 else x.split()[0])
                goal_keys_values.append((k, v))
                
        for k, v in zip(final_item['optionKeys'], final_item['optionValues']):
            if v:
                # If v is a list, sort it using custom key function
                if isinstance(v, list):
                    v = sorted(v, key=lambda x: x.split()[-1] if len(x.split()) > 1 else x.split()[0])
                final_keys_values.append((k, v))
        
        # Sort the key-value pairs
        goal_keys_values.sort()
        final_keys_values.sort()
        
        if goal_keys_values != final_keys_values:
            print(f"\nDifference in item {i + 1}:")
            print(f"❌ Options mismatch:")
            print(f"  Goal:  {goal_keys_values}")
            print(f"  Final: {final_keys_values}")
            return False
    
    return True

def run_parallel_simulations(num_simulations=10, max_workers=5, level="simple"):
    """Run multiple simulations in parallel using ThreadPoolExecutor"""
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all simulations
        future_to_sim = {
            executor.submit(run_simulation, level): i 
            for i in range(num_simulations)
        }
        
        # Process completed simulations
        for future in concurrent.futures.as_completed(future_to_sim):
            sim_num = future_to_sim[future]
            try:
                success = future.result()
                results.append(success)
                print(f"\nSimulation {sim_num} completed successfully: {success}")
            except Exception as e:
                print(f"\nSimulation {sim_num} generated an exception: {e}")
                results.append(False)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Print summary
    successful = sum(results)
    print(f"\n=== Final Summary ===")
    print(f"Total simulations: {num_simulations}")
    print(f"Successful: {successful}")
    print(f"Failed: {num_simulations - successful}")
    print(f"Total time: {duration:.2f} seconds")
    print(f"Average time per simulation: {duration/num_simulations:.2f} seconds")

if __name__ == "__main__":
    """Single Threaded"""
    # run_simulation(order_complexity="simple")
    # run_simulation(order_complexity="medium")
    run_simulation(order_complexity="complex")

    """Multi Threaded"""
    # Run parallel simulations with x simulations and y concurrent threads with z complexity
    # run_parallel_simulations(num_simulations=10, max_workers=5, level="simple")
    # run_parallel_simulations(num_simulations=5, max_workers=5, level="medium")
    # run_parallel_simulations(num_simulations=10, max_workers=5, level="complex")
