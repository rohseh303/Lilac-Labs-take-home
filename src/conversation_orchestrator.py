import random
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
import os
import time
import logging
from datetime import datetime

class ConversationOrchestrator:
    EMOTIONS = [
        "normal", "tired", "hungry", "rushed", "chill",
        "annoyed", "happy", "grumpy", "high", "drunk",
        "impatient", "distracted", "hangry", "quiet", "loud"
    ]
    TONES = [
        "casual", "rude", "polite", "quiet", "loud",
        "friendly", "short", "confused", "sleepy", "rushed",
        "mumbling", "clear", "demanding", "chill"
    ]
    BREVITIES = [
        "short", "normal", "long", "minimal",
        "chatty", "mumbled", "clear", "rushed"
    ]

    def __init__(self, lilac_client):
        # Set up logging
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{log_dir}/conversation_{timestamp}.log"
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Initialize other attributes
        self.lilac_client = lilac_client
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            self.logger.error("OPENAI_API_KEY environment variable not set")
            raise ValueError("OPENAI_API_KEY environment variable must be set")
            
        self.openai_client = OpenAI(api_key=self.api_key)
        self.conversation_context = {
            "ordered_items": [],
            "current_item": None,
            "pending_questions": [],
            "last_agent_message": None,
            "order_goal": [],
            "conversation_style": None,
            "items_in_progress": [],
            "chat_history": []
        }
        
        self.logger.info("ConversationOrchestrator initialized")

    def run_conversation(self, order_id: str, order_goal: List[Dict]) -> List[Dict]:
        """Simulate a natural customer conversation flow"""
        self.logger.info(f"NEW CHAT\n\n")
        self.conversation_context["chat_history"] = []  # Reset chat history at start
        messages_log = []
        self.conversation_context["order_goal"] = order_goal
        self.conversation_context["current_item"] = order_goal[0] if order_goal else None
        self.conversation_context["conversation_style"] = self._pick_random_style()
        state = "GREET"
        
        self.logger.info(f"Starting conversation with order_id: {order_id}")
        self.logger.debug(f"Initial conversation context: {self.conversation_context}")
        while state != "DONE":
            self.logger.info(f"\n\nNEW CHAT")
            try:
                time.sleep(1)
                self.logger.debug(f"Current state: {state}")
                customer_message = self._generate_customer_message(state)
                self.logger.info(f"Generated customer message: {customer_message}")
                
                # Check all pending questions against this response
                if self.conversation_context["pending_questions"]:
                    # Create a copy since we'll be modifying the list
                    questions = self.conversation_context["pending_questions"].copy()
                    for question in questions:
                        self._is_question_answered(question, customer_message)
                
                response = self.lilac_client.send_chat_message(order_id, customer_message)
                self.logger.debug(f"Received response: {response}")
                
                messages_log.extend([
                    {"role": "user", "content": customer_message},
                    {"role": "assistant", "content": response["messages"][-1]["content"]}
                ])

                self._update_conversation_context(response["messages"][-1]["content"], customer_message)
                state = self._get_next_state(state)
                self.logger.debug(f"Updated conversation context: {self.conversation_context}")
                self.logger.debug(f"Next state: {state}")

            except Exception as e:
                self.logger.error(f"Error in conversation loop: {e}", exc_info=True)
                state = "DONE"
                break

        self.logger.info("Conversation completed")
        return messages_log

    def _generate_customer_message(self, state: str) -> str:
        """Generate a contextually appropriate customer message"""
        style = self.conversation_context["conversation_style"]
        self.logger.debug(f"Using conversation style: {style}")
        
        system_prompt = self._build_system_prompt(state, style)
        user_prompt = self._build_user_prompt(state)
        
        self.logger.debug(f"System prompt: {system_prompt}")
        self.logger.debug(f"User prompt: {user_prompt}")
        
        response = self._get_gpt4_response(system_prompt, user_prompt)
        
        # Validate the response doesn't try to order unauthorized items
        if not self._is_response_valid(response):
            self.logger.warning("Generated response contained unauthorized orders, regenerating...")
            # Try again with a more explicit warning
            system_prompt += "\nWARNING: DO NOT ORDER ANY ITEMS. ONLY ASK QUESTIONS OR PROVIDE CLARIFICATION."
            response = self._get_gpt4_response(system_prompt, user_prompt)
        
        self.logger.info(f"GPT-4 response: {response}")
        return response

    def _build_system_prompt(self, state: str, style: Dict) -> str: # clarify the structure of the order, an order will look like...
        base_prompt = f"""
        You are a CUSTOMER ordering food at a drive-through restaurant.
        Current conversation state: {state}
        Emotion: {style['emotion']}
        Tone: {style['tone']}
        Brevity: {style['brevity']}
        
        Conversation Context:
        - ORDER LIST: {self.conversation_context["order_goal"]}
        - Current item to order: {self.conversation_context["current_item"]}
        - Building item: {self.conversation_context["items_in_progress"]}
        - Items already ordered: {self.conversation_context["ordered_items"]}
        - Pending questions from staff: {self.conversation_context["pending_questions"]}
        - Last staff message: {self.conversation_context["last_agent_message"]}

        NEVER ORDER SOMETHING NOT PROVIDED IN THE ORDER LIST. NEVER ADD EVEN TOPPINGS OR CUSTOMIZATIONS THAT ARE NOT PROVIDED IN THE ORDER LIST.
        ALWAYS USE THE PROPER NAMES FOR ITEMS AND OPTIONS.

        IMPORTANT:
        You are trying to order specific items but should act natural and spontaneous.
        Even though we have a list of items to order, act as if you don't know the menu.
        NEVER ORDER THE ENTIRE ITEM IN ONE MESSAGE.
        Customizations are only deviations from the basic item.
        Mention customizations but if there's a lot. Do them incrementally.

        Only respond with the exact words a customer would say - no explanations or meta commentary.
        If there's a mixup, ask the staff to clarify.
        """

        # Add context-specific instructions based on state
        state_contexts = {
            "GREET": "Generate a natural greeting.",
            "QUESTION": "Ask a relevant question about the menu or your order.",
            "ORDER": "Place or modify an order in a natural way.",
            "CLARIFY": "Respond to or ask for clarification about something.",
            "PRE-DONE": "Indicate you're finished ordering.",
            "DONE": "Assistant or you has ended the conversation"
        }
        
        return f"{base_prompt}\n{state_contexts.get(state, '')}"

    def _build_user_prompt(self, state: str) -> str:
        context = self.conversation_context
        
        if state == "ORDER" and context["current_item"]:
            return f"See what is missing in 'Building item' to complete final order: {context['current_item']['itemName']} with options: {context['current_item'].get('optionValues', [])}"
        elif state == "CLARIFY" and context["last_agent_message"]:
            return f"Respond to: {context['last_agent_message']}. IMPORTANT: DO NOT ORDER ANYTHING NOT IN THE ORDER LIST. IF SO, REMOVE IT"
        elif state == "QUESTION":
            # Pick something relevant to ask about
            topics = ["menu items", "prices", "customization options", "specials"]
            return f"Ask about: {random.choice(topics)}"
        elif state == "GREET":
            return "Generate a natural greeting."
        
        if len(self.conversation_context["order_goal"]) == 0:
            return "Verify the chat history matches the ordered items list. If needed, ask for clarification. Otherwise, end the conversation naturally."
        else:
            return "Continue the conversation naturally"
        
    def _is_response_valid(self, response: str) -> bool:
        """Check if the response doesn't try to order unauthorized items"""
        try:
            system_prompt = """
            You are validating if a customer's response follows the rules.
            
            Rules:
            1. If there are no items left to order (order_goal is empty), the customer should NOT try to order any new items
            2. If there are items to order, the customer should ONLY order items from the order_goal list
            3. Asking questions, seeking clarification, or responding to staff questions is always allowed
            
            Respond with only "true" if the response follows the rules, or "false" if it breaks them.
            """
            
            user_prompt = f"""
            Order goal (remaining items to order): {self.conversation_context['order_goal']}
            Customer's response: {response}

            Does this response follow the rules?
            """
            
            validation = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            
            result = validation.choices[0].message.content.strip().lower()
            self.logger.debug(f"Response validation result: {result}")
            return result == "true"
        
        except Exception as e:
            self.logger.error(f"Error in response validation: {e}", exc_info=True)
            # Default to True on error to avoid blocking valid responses
            return True

    def _update_conversation_context(self, agent_message: str, user_message: str):
        """Update conversation context based on agent's response"""
        self.logger.debug(f"Updating context with agent message: {agent_message}")
        
        # Update chat history
        self.conversation_context["chat_history"].extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": agent_message}
        ])
        
        self.conversation_context["last_agent_message"] = agent_message

        # check if the item is complete, if so, then don't update just yet, do the item is complete shit by setting a flag to skip over
        #  if not, we need to update item with data and then check again becasue it might've just been completed
        complete = self._is_item_completed(agent_message, self.conversation_context["current_item"], self.conversation_context["items_in_progress"])
        completed_before_update = complete
        if not complete:
            self._track_item_construction(agent_message, user_message)
            complete = self._is_item_completed(agent_message, self.conversation_context["current_item"], self.conversation_context["items_in_progress"])
        
        if self._needs_response(agent_message):
            self.conversation_context["pending_questions"].append(agent_message)
            self.logger.debug("Added pending question")
        
        # If current item was completed
        if complete:
            # If we have a current item, it means it was just ordered
            if self.conversation_context["current_item"]:
                # Handle completed item
                current_item = self.conversation_context["current_item"]
                self.conversation_context["ordered_items"].append(current_item)
                
                # Clear progress for completed item
                self.conversation_context["items_in_progress"] = []
                
                # Remove from order goal
                self.conversation_context["order_goal"] = [
                    item for item in self.conversation_context["order_goal"]
                    if not (item["itemName"] == current_item["itemName"] and 
                           item["optionValues"] == current_item["optionValues"])
                ]
                
                # Clear current item
                self.conversation_context["current_item"] = None
                self.logger.debug("Removed ordered item from goal and cleared current item")
                
            # Set new current_item if there are more items to order
            if self.conversation_context["order_goal"]:
                self.conversation_context["current_item"] = self.conversation_context["order_goal"][0]
                self.logger.debug(f"Updated current item to: {self.conversation_context['current_item']}")

            if not completed_before_update:
                self._track_item_construction(agent_message, user_message)
        
        self.logger.debug(f"New Context: {self.conversation_context}")

    def _is_item_completed(self, agent_message: str, goal_item: Optional[Dict], current_item: Optional[Dict]) -> bool:
        if not goal_item or not current_item:
            self.logger.debug("Item Completed Check: missing current_item")
            return False
            
        try:
            system_prompt = """
            Given the intended order and the current item, confirm if the two are the same more or less (formatting can be different)

            Examples that shoudl return true:
            intended_item: {'itemName': 'Plain Classic Hot Dog', 'optionKeys': ['customizations', 'meal option', 'side options', 'drink options'], 'optionValues': [['no mayo'], ['meal'], ['chili cheese fries'], ['rootbeer float']]}
            current_item: ['- new_item: Plain Classic Hot Dog', '- option: no mayo for sauce', '- meal_type: meal', '- option: chili cheese fries for side', '- option: rootbeer float for drink']

            Examples that should return false:
            intended_item: {'itemName': 'Plain Classic Hot Dog', 'optionKeys': ['customizations', 'meal option', 'side options', 'drink options'], 'optionValues': [['no mayo', 'add sauerkraut', 'easy mustard'], ['meal'], ['chili cheese fries'], ['rootbeer float']]}
            current_item: ['- new_item: Plain Classic Hot Dog', '- option: no mayo for sauce', '- option: sauerkraut for topping', '- option: light mustard for sauce', '- meal_type: meal']

            The names of the specific items should be the same. The structure and ordering doesn't matter. But all the actual items should be there.
            """
            
            user_prompt = f"""
            Intended order: {goal_item}
            Current item: {current_item}
            Does this confirm the item was successfully ordered? Return only "true" or "false".
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower()
            self.logger.info(f"Is Item Completed result: {result}")
            return result == "true"
            
        except Exception as e:
            self.logger.error(f"Error in GPT is item completed check: {e}", exc_info=True)
            self.logger.error(f"Failed message: '{agent_message}'")
            # Default to False on error to avoid accidentally removing items
            return False

    def _get_next_state(self, current_state: str) -> str:
        """Determine next state based on context and GPT-4 analysis"""
        try:
            # First, use GPT to analyze if this is a conversation ending
            if self._is_conversation_ending(self.conversation_context["last_agent_message"]):
                return "DONE"
            
            # Always check if we need to answer a question
            if self._needs_response(self.conversation_context["last_agent_message"]):
                return "CLARIFY"
            
            # If we're in DONE state and no questions to answer, stay in DONE
            if current_state == "DONE":
                return "DONE"
            
            # Use GPT-4 to determine the next most appropriate state
            system_prompt = """
            You are analyzing a drive-through conversation to determine the most appropriate next state.
            Available states: GREET, QUESTION, ORDER, CLARIFY, PRE-DONE, DONE
            
            Consider:
            1. If items remain to be ordered, ORDER should be prioritized
            2. If confusion exists or a question is pending, CLARIFY should be chosen
            3. If information is needed, QUESTION is appropriate
            4. If all items are ordered, PRE-DONE is appropriate
            5. If you or the assistant has ended the conversation, DONE is appropriate
            
            Respond with only one word: the next state.
            """
            
            context_prompt = f"""
            Current state: {current_state}
            Remaining items to order: {self.conversation_context['order_goal']}
            Current item: {self.conversation_context['current_item']}
            Ordered items: {self.conversation_context['ordered_items']}
            Pending questions: {self.conversation_context['pending_questions']}
            Last staff message: {self.conversation_context['last_agent_message']}
            
            What should be the next conversation state?
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            
            next_state = response.choices[0].message.content.strip().upper()
            self.logger.debug(f"GPT suggested next state: {next_state}")
            
            # Validate the state is valid, default to DONE if not
            valid_states = {"GREET", "QUESTION", "ORDER", "CLARIFY", "PRE-DONE", "DONE"}
            return next_state if next_state in valid_states else "DONE"
            
        except Exception as e:
            self.logger.error(f"Error in get_next_state: {e}", exc_info=True)
            return "DONE"  # Default to DONE on error

    def _is_conversation_ending(self, agent_message: str) -> bool:
        """Use GPT to determine if the message indicates the conversation should end"""
        try:
            system_prompt = """
            You are analyzing a restaurant staff's response to determine if it indicates the conversation should end.
            Respond with only "true" or "false".
            
            Examples of ending messages:
            - "Please pull forward. Thanks!"
            - "See you at the window!"
            - "Have a great day!"
            - "Your total is $X. Please pull forward."
            
            Examples of non-ending messages:
            - "Would you like anything else?"
            - "What size would you like?"
            - "I've added that to your order."
            - "The burger costs $10.99"
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Message: {agent_message}\nDoes this message indicate the conversation should end?"}
                ],
                temperature=0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower()
            self.logger.debug(f"GPT conversation ending analysis: {result}")
            return result == "true"
            
        except Exception as e:
            self.logger.error(f"Error in GPT conversation ending check: {e}", exc_info=True)
            # Default to False on error to avoid prematurely ending conversations
            return False

    def _pick_random_style(self) -> Dict[str, str]:
        """Generate a random conversation style once at the start"""
        return {
            "emotion": random.choice(self.EMOTIONS),
            "tone": random.choice(self.TONES),
            "brevity": random.choice(self.BREVITIES)
        }

    def _get_gpt4_response(self, system_prompt: str, user_prompt: str) -> str:
        try:
            self.logger.debug("Sending request to GPT-4")
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                # max_tokens=50,
                presence_penalty=-0.1,
                frequency_penalty=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error getting GPT-4 response: {e}", exc_info=True)
            if "order" in user_prompt.lower():
                return "`I'd like `to order that, please."
            return "Yes, please."

    def _needs_response(self, agent_message: str) -> bool:
        """
        Use GPT-4 to determine if the agent's message requires a customer response
        and what type of response is appropriate.
        """
        if not agent_message:
            return False
        
        try:
            system_prompt = """
            You are analyzing a restaurant staff's message to determine if it requires a customer response about a specific item in their order.
            Respond with only "true" or "false".
            
            Examples requiring response:
            - "What size drink would you like?"
            - "Would you like any toppings on that?"
            - "Do you want that as a meal or a la carte?"
            - "Which type of cheese would you prefer?"
            
            Examples NOT requiring response:
            - "I've added that to your order"
            - "Would you like anything else?"
            - "Anything else you'd like to order?"
            - "Your total is $15.99"
            - "Please pull forward"
            - "Have a great day!"
            - "Got it, one burger coming up"
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Message: {agent_message}\nDoes this message require a direct response about the order?"}
                ],
                temperature=0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower() == "true"
            self.logger.debug(f"GPT response analysis: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in GPT response check: {e}", exc_info=True)
            # Fall back to simple question mark check if GPT fails
            return "?" in agent_message

    def _is_question_answered(self, question: str, customer_response: str) -> bool:
        """
        Check if a question was adequately answered and remove it from pending_questions if so.
        Returns True if the question was answered.
        """
        try:
            system_prompt = """
            You are analyzing a conversation to determine if a question was adequately answered.
            Respond with only "true" or "false".
            
            Examples:
            Question: "Would you like fries with that?"
            Response: "Yes, please" -> true
            Response: "No thanks" -> true
            Response: "How much are they?" -> false (asks another question instead)
            
            Question: "What size drink would you like?"
            Response: "Medium" -> true
            Response: "What sizes do you have?" -> false
            
            Question: "Anything else?"
            Response: "No, that's all" -> true
            Response: "Yeah, can I also get..." -> true
            Response: "What's your hours?" -> false
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Question: {question}\nResponse: {customer_response}\nWas the question adequately answered?"}
                ],
                temperature=0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower() == "true"
            self.logger.debug(f"GPT question-answer analysis: {result}")
            
            # If the question was answered, remove it from pending_questions using remove()
            if result and question in self.conversation_context["pending_questions"]:
                self.conversation_context["pending_questions"].remove(question)
                self.logger.debug(f"Removed answered question: {question}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in GPT question-answer check: {e}", exc_info=True)
            return False
        
    def _track_item_construction(self, agent_message: str, user_message: str):
        """
        Track what's being constructed based on the entire conversation context.
        Uses chat history to understand if items are part of a meal or standalone.
        """
        try:
            system_prompt = """
                Analyze both customer and staff messages to determine:
                1. If a new item is being ordered (respond with "new_item: [item name]")
                2. If options/modifications are being specified (respond with one or more lines of "option: [option value] for [option type]")
                3. If a meal choice is specified (respond with "meal_type: meal" or "meal_type: a la carte")
                4. If neither, respond with "none"
                
                CONTEXT:
                - When items are ordered as part of a meal, the sides and drinks are options of the main item
                - When items are ordered separately (not as part of a meal), they are new items
                - Each main item can have customizations, sides, and drinks as options
                
                EXAMPLES:
                Conversation 1 (Meal):
                Customer: "I want a burger"
                Staff: "Would you like that as a meal?"
                Customer: "Yes, with fries and a coke"
                Staff: "Added burger meal with fries and coke."

                Latest exchange:
                Customer: "Yes, with fries and a coke"
                Staff: "Added burger meal with fries and coke."

                New: 
                - meal_type: meal
                - option: fries for side
                - option: coke for drink

                Already added:
                - new_item: burger

                Output:
                - new_item: burger
                - meal_type: meal
                - option: fries for side
                - option: coke for drink

                Note: The burger item would have already been added in the previous call to this function. But it's other modifieres were clarified in the latest exchange.
                
                Analyze the latest agent and user messages in the context of the conversation to see how best to modify the existing items list.
                """
            
            # Format the entire chat history
            chat_context = "\n".join([
                f"{'Customer' if msg['role'] == 'user' else 'Staff'}: {msg['content']}"
                for msg in self.conversation_context["chat_history"]
            ])
            
            user_prompt = f"""
            FULL CONVERSATION:
            {chat_context}
            
            LATEST EXCHANGE:
            Customer: {user_message}
            Staff: {agent_message}

            LATEST ITEM BUILD: {self.conversation_context["items_in_progress"]} 
            
            Return the updated items list.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=150
            )
            
            results = response.choices[0].message.content.strip().split('\n')

            self.conversation_context["items_in_progress"] = results
            self.logger.debug(f"CALLED NEW BUILD LIST: {self.conversation_context['items_in_progress']}")

        except Exception as e:
            self.logger.error(f"Error tracking item construction: {e}", exc_info=True)
        