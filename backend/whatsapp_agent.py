# backend/whatsapp_agent.py

import json

from real_estate_client import (
    get_properties_by_location,
    search_properties
)

from property_llm import (
    find_properties_for_customer
)


# ============================================================
# CUSTOMER STATE
# ============================================================

def create_new_customer_state():
    """
    Create a new conversation state for a customer.
    """

    return {
        "mode": "guided",

        "step": "intent",

        "guided_steps": 0,

        "requirements": {},

        "conversation_history": [],

        "last_results": []
    }


# ============================================================
# BUTTON RESPONSE
# ============================================================

def button_response(text, buttons):
    """
    Creates a standard button response.
    """

    return {
        "type": "buttons",
        "text": text,
        "buttons": buttons
    }


# ============================================================
# FREE TEXT RESPONSE
# ============================================================

def free_text_response(text):
    """
    Creates a response that asks the customer
    to enter free text.
    """

    return {
        "type": "free_text",
        "text": text
    }


# ============================================================
# PROPERTY RESULT RESPONSE
# ============================================================

def property_response(properties):
    """
    Creates a property-result response.

    Later this will be converted into actual
    WhatsApp messages/cards.
    """

    return {
        "type": "property_results",
        "total": len(properties),
        "properties": properties
    }


# ============================================================
# HANDLE CUSTOMER MESSAGE
# ============================================================

def handle_message(state, message):

    message = message.strip()

    if not message:
        return {
            "type": "text",
            "text": "Please send a message."
        }


    # ========================================================
    # SAVE CUSTOMER MESSAGE
    # ========================================================

    state["conversation_history"].append({
        "role": "user",
        "content": message
    })


    # ========================================================
    # GUIDED MODE
    # ========================================================

    if state["mode"] == "guided":


        # ====================================================
        # STEP 1 — INTENT
        # ====================================================

        if state["step"] == "intent":

            # -----------------------------
            # GREETING
            # -----------------------------

            if message.lower() in [
                "hi",
                "hello",
                "hey"
            ]:

                response = button_response(
                    "Hi 👋 Welcome!\n\n"
                    "What are you looking for?",
                    [
                        "Buy Property",
                        "Rent Property"
                    ]
                )

                state["conversation_history"].append({
                    "role": "assistant",
                    "content": json.dumps(response)
                })

                return response


            # -----------------------------
            # BUY
            # -----------------------------

            if message.lower() == "buy property":

                state["requirements"]["intent"] = "buy"

                state["guided_steps"] += 1

                state["step"] = "city"

                response = button_response(
                    "Great! Which city are you "
                    "looking in?",
                    [
                        "Gurgaon",
                        "Noida",
                        "Delhi",
                        "Ghaziabad"
                    ]
                )

                state["conversation_history"].append({
                    "role": "assistant",
                    "content": json.dumps(response)
                })

                return response


            # -----------------------------
            # RENT
            # -----------------------------

            if message.lower() == "rent property":

                state["requirements"]["intent"] = "rent"

                state["guided_steps"] += 1

                state["step"] = "city"

                response = button_response(
                    "Great! Which city are you "
                    "looking in?",
                    [
                        "Gurgaon",
                        "Noida",
                        "Delhi",
                        "Ghaziabad"
                    ]
                )

                state["conversation_history"].append({
                    "role": "assistant",
                    "content": json.dumps(response)
                })

                return response


            response = button_response(
                "Welcome! What are you looking for?",
                [
                    "Buy Property",
                    "Rent Property"
                ]
            )

            state["conversation_history"].append({
                "role": "assistant",
                "content": json.dumps(response)
            })

            return response


        # ====================================================
        # STEP 2 — CITY
        # ====================================================

        elif state["step"] == "city":

            cities = {
                "gurgaon": "Gurgaon",
                "noida": "Noida",
                "delhi": "Delhi",
                "ghaziabad": "Ghaziabad"
            }

            city = cities.get(
                message.lower()
            )


            if city:

                state["requirements"]["city"] = city

                state["guided_steps"] += 1


                # ------------------------------------------------
                # MCP CALL
                # ------------------------------------------------

                try:

                    properties = get_properties_by_location(
                        city
                    )

                    state["last_results"] = properties

                except Exception as error:

                    print(
                        "MCP ERROR:",
                        error
                    )

                    properties = []


                # ------------------------------------------------
                # NEXT QUESTION
                # ------------------------------------------------

                state["step"] = "property_type"

                response = button_response(
                    f"Great! I found "
                    f"{len(properties)} properties "
                    f"in {city}.\n\n"
                    "What type of property are "
                    "you looking for?",
                    [
                        "2 BHK",
                        "3 BHK",
                        "4 BHK",
                        "Villa"
                    ]
                )

                state["conversation_history"].append({
                    "role": "assistant",
                    "content": json.dumps(response)
                })

                return response


            response = button_response(
                "Please select a city:",
                [
                    "Gurgaon",
                    "Noida",
                    "Delhi",
                    "Ghaziabad"
                ]
            )

            state["conversation_history"].append({
                "role": "assistant",
                "content": json.dumps(response)
            })

            return response


        # ====================================================
        # STEP 3 — PROPERTY TYPE
        # ====================================================

        elif state["step"] == "property_type":


            # ------------------------------------------------
            # 2 / 3 / 4 BHK
            # ------------------------------------------------

            if message.lower() in [
                "2 bhk",
                "3 bhk",
                "4 bhk"
            ]:

                bhk = int(
                    message.split()[0]
                )

                state["requirements"]["bhk"] = bhk

                state["guided_steps"] += 1


                # ------------------------------------------------
                # MCP SEARCH
                # ------------------------------------------------

                try:

                    properties = search_properties(
                        city=state["requirements"]["city"],
                        bhk=bhk
                    )

                    state["last_results"] = properties

                except Exception as error:

                    print(
                        "MCP ERROR:",
                        error
                    )

                    properties = []


                # ------------------------------------------------
                # SWITCH TO AI MODE
                # ------------------------------------------------

                state["mode"] = "ai"

                state["step"] = "free_search"


                response = free_text_response(

                    f"Perfect — you're looking for "
                    f"a {bhk} BHK in "
                    f"{state['requirements']['city']}.\n\n"

                    f"I found {len(properties)} "
                    f"matching properties so far.\n\n"

                    "Now tell me what else you need "
                    "in your own words.\n\n"

                    "For example:\n"
                    "\"Under 1.2 crore, near metro, "
                    "with parking\""

                )


                state["conversation_history"].append({
                    "role": "assistant",
                    "content": json.dumps(response)
                })

                return response


            # ------------------------------------------------
            # VILLA
            # ------------------------------------------------

            if message.lower() == "villa":

                state["requirements"][
                    "property_type"
                ] = "Villa"

                state["guided_steps"] += 1


                # ------------------------------------------------
                # MCP SEARCH
                # ------------------------------------------------

                try:

                    properties = search_properties(
                        city=state["requirements"]["city"],
                        property_type="Villa"
                    )

                    state["last_results"] = properties

                except Exception as error:

                    print(
                        "MCP ERROR:",
                        error
                    )

                    properties = []


                # ------------------------------------------------
                # SWITCH TO AI MODE
                # ------------------------------------------------

                state["mode"] = "ai"

                state["step"] = "free_search"


                response = free_text_response(

                    "Perfect — you're looking for "
                    f"a villa in "
                    f"{state['requirements']['city']}.\n\n"

                    f"I found {len(properties)} "
                    "matching properties so far.\n\n"

                    "Now tell me the rest of your "
                    "requirements in your own words."

                )


                state["conversation_history"].append({
                    "role": "assistant",
                    "content": json.dumps(response)
                })

                return response


            response = button_response(
                "Please select a property type:",
                [
                    "2 BHK",
                    "3 BHK",
                    "4 BHK",
                    "Villa"
                ]
            )

            state["conversation_history"].append({
                "role": "assistant",
                "content": json.dumps(response)
            })

            return response


    # ========================================================
    # AI MODE
    # ========================================================

    if state["mode"] == "ai":

        print("\n==============================")
        print("AI SEARCH")
        print("==============================")


        # ----------------------------------------------------
        # BUILD AI QUERY
        # ----------------------------------------------------

        ai_query = message


        # ----------------------------------------------------
        # CALL EXISTING PROPERTY LLM
        # ----------------------------------------------------

        try:

            results = find_properties_for_customer(
                ai_query,
                state["conversation_history"]
            )

            state["last_results"] = (
                results.get("results", [])
            )


        except Exception as error:

            print(
                "LLM ERROR:",
                error
            )

            response = {
                "type": "text",
                "text": (
                    "Sorry, I couldn't search "
                    "the properties right now."
                )
            }

            state["conversation_history"].append({
                "role": "assistant",
                "content": json.dumps(response)
            })

            return response


        # ----------------------------------------------------
        # RETURN PROPERTY RESULTS
        # ----------------------------------------------------

        # response = {
        #     "type": "ai_results",
        #     "customer_query": ai_query,
        #     "total_matches": results.get(
        #         "total_matches",
        #         0
        #     ),
        #     "results": results.get(
        #         "results",
        #         []
        #     )
        # }
        response = {
            "type": "ai_results",
            "customer_query": ai_query,
            "total_matches": results.get(
                "total_matches",
                0
            ),
            "results": results.get(
                "results",
                []
            )
        }

        state["conversation_history"].append({
            "role": "assistant",
            "content": json.dumps(response)
        })

        return response


        # IMPORTANT:
        #
        # property_llm.py already stores the
        # user message and AI response in its
        # conversation_history.
        #
        # Therefore we DO NOT append another
        # copy here.


        # return response


    # ========================================================
    # FALLBACK
    # ========================================================

    response = {
        "type": "text",
        "text": (
            "I didn't quite understand that."
        )
    }

    state["conversation_history"].append({
        "role": "assistant",
        "content": json.dumps(response)
    })

    return response


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    state = create_new_customer_state()


    # --------------------------------------------------------
    # QUERY 1
    # --------------------------------------------------------

    print("\nCUSTOMER:")
    print("Hi")

    response = handle_message(
        state,
        "Hi"
    )

    print("\nBOT:")
    print(response)


    # --------------------------------------------------------
    # QUERY 2
    # --------------------------------------------------------

    print("\nCUSTOMER:")
    print("Buy Property")

    response = handle_message(
        state,
        "Buy Property"
    )

    print("\nBOT:")
    print(response)


    # --------------------------------------------------------
    # QUERY 3
    # --------------------------------------------------------

    print("\nCUSTOMER:")
    print("Gurgaon")

    response = handle_message(
        state,
        "Gurgaon"
    )

    print("\nBOT:")
    print(response)


    # --------------------------------------------------------
    # QUERY 4
    # --------------------------------------------------------

    print("\nCUSTOMER:")
    print("3 BHK")

    response = handle_message(
        state,
        "3 BHK"
    )

    print("\nBOT:")
    print(response)


    # --------------------------------------------------------
    # QUERY 5
    # --------------------------------------------------------

    print("\nCUSTOMER:")
    print(
        "Under 1.2 crore, near metro and parking"
    )

    response = handle_message(
        state,
        "Under 1.2 crore, near metro and parking"
    )

    print("\nBOT:")
    print(
        json.dumps(
            response,
            indent=2
        )
    )


    # --------------------------------------------------------
    # FINAL STATE
    # --------------------------------------------------------

    print("\n==============================")
    print("FINAL CUSTOMER STATE")
    print("==============================")

    print(
        json.dumps(
            state,
            indent=2
        )
    )