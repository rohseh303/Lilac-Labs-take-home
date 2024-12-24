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
    
    TRANSITIONS = {
        "GREET": [
            ("QUESTION", 0.6),
            ("ORDER", 0.3),
        ],
        "QUESTION": [
            ("ORDER", 0.5),
            ("CLARIFY", 0.2),
            ("DONE", 0.2),
        ],
        "ORDER": [
            ("QUESTION", 0.3),
            ("DONE", 0.5),
        ],
        "CLARIFY": [
            ("QUESTION", 0.7),
        ],
        "ANSWER": [
            ("ORDER", 0.6),
            ("DONE", 0.4),
        ],
        "DONE": []
    }

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
            "conversation_style": None
        }
        
        self.logger.info("ConversationOrchestrator initialized")

    def run_conversation(self, order_id: str, order_goal: List[Dict]) -> List[Dict]:
        """Simulate a natural customer conversation flow"""
        self.logger.info(f"NEW CHAT\n\n")
        messages_log = []
        self.conversation_context["order_goal"] = order_goal
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

                self._update_conversation_context(response["messages"][-1]["content"])
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
        self.logger.info(f"GPT-4 response: {response}")
        return response

    def _build_system_prompt(self, state: str, style: Dict) -> str:
        base_prompt = f"""
        You are a CUSTOMER ordering food at a drive-through restaurant. You are NOT the restaurant staff.
        Current conversation state: {state}
        Emotion: {style['emotion']}
        Tone: {style['tone']}
        Brevity: {style['brevity']}
        
        Conversation Context:
        - ORDER LIST: {self.conversation_context["order_goal"]}
        - Current item to order: {self.conversation_context["current_item"]}
        - Items already ordered: {self.conversation_context["ordered_items"]}
        - Pending questions from staff: {self.conversation_context["pending_questions"]}
        - Last staff message: {self.conversation_context["last_agent_message"]}

        NEVER ORDER SOMETHING NOT PROVIDED IN THE ORDER LIST. NEVER ADD EVEN TOPPINGS OR CUSTOMIZATIONS THAT ARE NOT PROVIDED IN THE ORDER LIST.

        IMPORTANT: You are the CUSTOMER. Respond as a customer would to the restaurant staff.
        You are trying to order specific items but should act natural and spontaneous.
        Even though we have a list of items to order, act as if you don't know the menu.
        Don't mention customizations until asked if we want to make changes.

        Only respond with the exact words a customer would say - no explanations or meta commentary.
        Never pretend to be the restaurant staff.
        """

        # Add context-specific instructions based on state
        state_contexts = {
            "GREET": "Generate a natural greeting.",
            "QUESTION": "Ask a relevant question about the menu or your order.",
            "ORDER": "Place or modify an order in a natural way.",
            "CLARIFY": "Respond to or ask for clarification about something.",
            "DONE": "Indicate you're finished ordering."
        }
        
        return f"{base_prompt}\n{state_contexts.get(state, '')}"

    def _build_user_prompt(self, state: str) -> str:
        context = self.conversation_context
        
        if state == "ORDER" and context["current_item"]:
            return f"Order {context['current_item']['itemName']} with options: {context['current_item'].get('optionValues', [])}"
        elif state == "CLARIFY" and context["last_agent_message"]:
            return f"Respond to: {context['last_agent_message']}"
        elif state == "QUESTION":
            # Pick something relevant to ask about
            topics = ["menu items", "prices", "customization options", "specials"]
            return f"Ask about: {random.choice(topics)}"
        
        if len(self.conversation_context["order_goal"]) == 0:
            return "End the conversation naturally"
        else:
            return "Continue the conversation naturally"

    def _update_conversation_context(self, agent_message: str):
        """Update conversation context based on agent's response"""
        self.logger.debug(f"Updating context with agent message: {agent_message}")
        
        self.conversation_context["last_agent_message"] = agent_message
        
        if self._needs_response(agent_message):
            self.conversation_context["pending_questions"].append(agent_message)
            self.logger.debug("Added pending question")
        
        # Use GPT to determine if the item was successfully ordered
        if self._is_order_confirmation(agent_message, self.conversation_context["current_item"]):
            # If we have a current item, it means it was just ordered
            if self.conversation_context["current_item"]:
                current_item = self.conversation_context["current_item"]
                # Add to ordered_items
                self.conversation_context["ordered_items"].append(current_item)
                
                # Remove from order_goal - using list comprehension for exact match
                self.conversation_context["order_goal"] = [
                    item for item in self.conversation_context["order_goal"]
                    if not (item["itemName"] == current_item["itemName"] and 
                           item["optionValues"] == current_item["optionValues"])
                ]
                
                # Clear current item
                self.conversation_context["current_item"] = None
                self.logger.debug(f"Removed ordered item from goal and cleared current item")
                
            # Set new current_item if there are more items to order
            if self.conversation_context["order_goal"]:
                self.conversation_context["current_item"] = self.conversation_context["order_goal"][0]
                self.logger.debug(f"Updated current item to: {self.conversation_context['current_item']}")
        
        self.logger.debug(f"New Context: {self.conversation_context}")

    def _is_order_confirmation(self, agent_message: str, goal_item: Optional[Dict], current_item: Optional[Dict]) -> bool:
        """
        Use GPT to determine if the message confirms an item was successfully ordered and matches our goal
        Args:
            agent_message: The staff's response
            goal_item: The item we're trying to order (from order_goal)
            current_item: The item currently being discussed
        """
        if not goal_item or not current_item:
            return False
            
        try:
            system_prompt = """
            You are analyzing a restaurant staff's response to determine if it confirms a specific item was successfully ordered.
            You will be given the intended order and need to verify the staff's response confirms that exact item.
            Respond with only "true" or "false".
            
            Examples:
            Intended: Cheeseburger with bacon
            "I've added a cheeseburger with bacon to your order" -> true
            "I've added a hamburger to your order" -> false
            "Got it, one cheeseburger coming up" -> false (missing bacon)
            
            Intended: Large Coke
            "One large Coke added" -> true
            "I've added your drink" -> false (size not confirmed)
            "Medium Coke has been added" -> false (wrong size)
            """
            
            user_prompt = f"""
            Intended order: {goal_item['itemName']} with options: {goal_item.get('optionValues', [])}
            Staff message: {agent_message}
            Does this confirm the exact item was successfully ordered?
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
            self.logger.debug(f"GPT order confirmation analysis: {result}")
            return result == "true"
            
        except Exception as e:
                self.logger.error(f"Error in GPT order confirmation check: {e}", exc_info=True)
                # Default to False on error to avoid accidentally removing items
                return False

    # def _is_order_confirmation(self, agent_message: str, goal_item: str, current_item: str) -> bool:
    #     """Use GPT to determine if the message confirms an item was successfully ordered"""
    #     try:
    #         system_prompt = """
    #         You are analyzing a restaurant staff's response to determine if it confirms an item was successfully ordered.
    #         Respond with only "true" or "false".
            
    #         Examples of confirmations:
    #         - "I've added that to your order"
    #         - "Your burger meal has been added"
    #         - "Got it, one coffee coming right up"
    #         - "Alright, that's been added to your total"
            
    #         Examples of non-confirmations:
    #         - "Would you like anything else?"
    #         - "What size would you like?"
    #         - "I'm sorry, could you repeat that?"
    #         - "We're out of that item"
    #         """
            
    #         response = self.openai_client.chat.completions.create(
    #             model="gpt-4",
    #             messages=[
    #                 {"role": "system", "content": system_prompt},
    #                 {"role": "user", "content": f"Message: {agent_message}\nDoes this confirm an item was successfully ordered?"}
    #             ],
    #             temperature=0,
    #             max_tokens=10
    #         )
            
    #         result = response.choices[0].message.content.strip().lower()
    #         self.logger.debug(f"GPT order confirmation analysis: {result}")
    #         return result == "true"
            
    #     except Exception as e:
    #         self.logger.error(f"Error in GPT order confirmation check: {e}", exc_info=True)
    #         # Default to False on error to avoid accidentally removing items
    #         return False

    def _get_next_state(self, current_state: str) -> str:
        """Determine next state based on context and GPT-4 analysis"""
        try:
            # First, use GPT to analyze if this is a conversation ending
            if self._is_conversation_ending(self.conversation_context["last_agent_message"]):
                return "DONE"
            
            # Always check if we need to answer a question
            if self._needs_response(self.conversation_context["last_agent_message"]):
                return "ANSWER"
            
            # If we're in DONE state and no questions to answer, stay in DONE
            if current_state == "DONE":
                return "DONE"
            
            # Use GPT-4 to determine the next most appropriate state
            system_prompt = """
            You are analyzing a drive-through conversation to determine the most appropriate next state.
            Available states: GREET, QUESTION, ORDER, CLARIFY, DONE
            
            Consider:
            1. If items remain to be ordered, ORDER should be prioritized
            2. If confusion exists or a question is pending, CLARIFY should be chosen
            3. If information is needed, QUESTION is appropriate
            4. If all items are ordered and all questions answered, DONE is appropriate
            
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
            valid_states = {"GREET", "QUESTION", "ORDER", "CLARIFY", "DONE", "ANSWER"}
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

    # def _adjust_transition_probabilities(self, transitions: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    #     """Adjust transition probabilities based on conversation context"""
    #     context = self.conversation_context
    #     adjusted = transitions.copy()
        
    #     # Increase probability of ORDER if we have pending items
    #     if context["order_goal"] and ("ORDER", 0.3) in adjusted:
    #         idx = adjusted.index(("ORDER", 0.3))
    #         adjusted[idx] = ("ORDER", 0.6)
            
    #     # Increase probability of CLARIFY if we have pending questions
    #     if context["pending_questions"] and ("CLARIFY", 0.2) in adjusted:
    #         idx = adjusted.index(("CLARIFY", 0.2))
    #         adjusted[idx] = ("CLARIFY", 0.4)
            
    #     return adjusted

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
                return "I'd like to order that, please."
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
        