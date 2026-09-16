import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from real_estate_client import (
    get_all_properties,
    get_property_details
)


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# ---------------------------------------------------------
# PREPARE PROPERTY DATA
# ---------------------------------------------------------

def prepare_properties(properties):

    compact_properties = []

    for property in properties:

        compact_properties.append({
            "id": property["property_id"],
            "title": property["title"],
            "city": property["city"],
            "location": property["location"],
            "type": property["property_type"],
            "bhk": property["bhk"],
            "price": property["price"],
            "area": property["area_sqft"],
            "parking": bool(property["parking"]),
            "furnished": property["furnished"],
            "metro_km": property["metro_distance_km"]
        })

    return compact_properties


# ---------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------

SYSTEM_PROMPT = """

You are an AI Real Estate Sales Copilot.

Your job is to understand a customer's property
requirements and select the 10 best properties from
the provided inventory.

You are operating inside an ongoing conversation.

The customer may refer to previous messages or
previously suggested properties using phrases such as:

- "these are too expensive"
- "show me cheaper ones"
- "what about Noida?"
- "I need something closer to the metro"
- "show me bigger ones"
- "I don't need parking anymore"
- "show me the first one"
- "compare the second and third"
- "these don't work for me"

You MUST use the conversation history to understand
what the customer means.

IMPORTANT RULES:

1. Consider ALL properties in the provided inventory.

2. Return a maximum of 10 properties.

3. Rank properties from best match to worst match.

4. Carefully understand the customer's requirements.

5. Use the conversation history to understand
   requirements that were mentioned earlier.

6. Treat the latest customer message as an update
   to the previous requirements when appropriate.

7. Preserve previous requirements unless the customer
   clearly changes or removes them.

8. Distinguish between hard requirements and preferences.

9. Prioritize hard requirements.

10. If exact matches exist, prioritize them.

11. If exact matches do not exist, DO NOT return
    an empty result.

12. Instead, find the closest alternatives by
    intelligently relaxing less important requirements.

13. Clearly explain what requirement differs for
    an alternative property.

14. NEVER invent properties.

15. ONLY return property IDs that exist in the inventory.

16. NEVER invent property information.

17. Do not return property prices, areas, amenities
    or other factual details from your own knowledge.
    Those will be retrieved separately from the database.

18. match_score must be between 0 and 100.

19. Return ONLY valid JSON.

Use this exact structure:

{
    "results": [
        {
            "property_id": "PROP-XXXX",
            "rank": 1,
            "match_score": 95,
            "match_type": "exact",
            "why_match": "Short explanation"
        }
    ]
}

The match_type must be one of:

"exact"
"close"
"alternative"

"""


# ---------------------------------------------------------
# FIND PROPERTIES FOR ONE CONVERSATION TURN
# ---------------------------------------------------------

def find_properties_for_customer(
    user_query,
    conversation_history
):

    # -----------------------------------------------------
    # GET COMPLETE PROPERTY INVENTORY
    # -----------------------------------------------------

    properties = get_all_properties()


    # -----------------------------------------------------
    # CREATE COMPACT PROPERTY DATA
    # -----------------------------------------------------

    compact_properties = prepare_properties(
        properties
    )

    property_data = json.dumps(
        compact_properties,
        separators=(",", ":")
    )


    # -----------------------------------------------------
    # BUILD MESSAGES FOR OPENAI
    # -----------------------------------------------------

    messages = [

        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }

    ]


    # -----------------------------------------------------
    # ADD COMPLETE CONVERSATION HISTORY
    # -----------------------------------------------------

    for message in conversation_history:

        messages.append({
            "role": message["role"],
            "content": message["content"]
        })


    # -----------------------------------------------------
    # ADD CURRENT CUSTOMER MESSAGE
    # -----------------------------------------------------

    current_user_prompt = f"""

CURRENT CUSTOMER MESSAGE:

{user_query}


PROPERTY INVENTORY:

{property_data}

"""

    messages.append({

        "role": "user",

        "content": current_user_prompt

    })


    # -----------------------------------------------------
    # CALL OPENAI
    # -----------------------------------------------------

    response = client.chat.completions.create(

        model="gpt-5.6-luna",

        messages=messages,

        response_format={
            "type": "json_object"
        }

    )


    # -----------------------------------------------------
    # PARSE LLM RESPONSE
    # -----------------------------------------------------

    llm_result = json.loads(

        response.choices[0].message.content

    )


    # -----------------------------------------------------
    # VERIFY PROPERTY IDS
    # -----------------------------------------------------

    valid_property_ids = {

        property["property_id"]

        for property in properties

    }


    verified_results = []


    for result in llm_result.get(
        "results",
        []
    ):

        property_id = result.get(
            "property_id"
        )


        # Ignore invalid / hallucinated property IDs.

        if property_id not in valid_property_ids:

            continue


        verified_results.append(
            result
        )


    # -----------------------------------------------------
    # GET AUTHORITATIVE PROPERTY DETAILS
    # -----------------------------------------------------

    final_results = []


    for result in verified_results:

        property_details = get_property_details(

            result["property_id"]

        )


        final_results.append({

            "property_id":
                result["property_id"],

            "rank":
                result["rank"],

            "match_score":
                result["match_score"],

            "match_type":
                result["match_type"],

            "why_match":
                result["why_match"],

            "property":
                property_details

        })


    # -----------------------------------------------------
    # CREATE FINAL RESPONSE
    # -----------------------------------------------------

    final_response = {

        "customer_query":
            user_query,

        "total_matches":
            len(final_results),

        "results":
            final_results

    }


    # -----------------------------------------------------
    # STORE USER MESSAGE
    # -----------------------------------------------------

    # conversation_history.append({

    #     "role": "user",

    #     "content": user_query

    # })


    # # -----------------------------------------------------
    # # STORE AI RESPONSE
    # # -----------------------------------------------------

    # conversation_history.append({

    #     "role": "assistant",

    #     "content": json.dumps(
    #         final_response
    #     )

    # })


    # -----------------------------------------------------
    # RETURN RESPONSE
    # -----------------------------------------------------

    return final_response


# ---------------------------------------------------------
# CONTINUOUS CONVERSATION TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    # This list represents ONE customer's conversation.

    conversation_history = []


    # -----------------------------------------------------
    # QUERY 1
    # -----------------------------------------------------

    query = """
    I need a 3 BHK in Gurgaon under 1.2 crore.
    Parking is important and I would prefer
    something close to the metro.
    """

    results = find_properties_for_customer(
        query,
        conversation_history
    )

    print("\n==============================")
    print("QUERY 1")
    print("==============================")

    print(
        f"Matches: {results['total_matches']}"
    )


    # -----------------------------------------------------
    # QUERY 2
    # -----------------------------------------------------

    query = """
    These are too expensive.
    Show me cheaper options.
    """

    results = find_properties_for_customer(
        query,
        conversation_history
    )

    print("\n==============================")
    print("QUERY 2")
    print("==============================")

    print(
        f"Matches: {results['total_matches']}"
    )


    # -----------------------------------------------------
    # QUERY 3
    # -----------------------------------------------------

    query = """
    Okay, now show me something closer to the metro.
    """

    results = find_properties_for_customer(
        query,
        conversation_history
    )

    print("\n==============================")
    print("QUERY 3")
    print("==============================")

    print(
        f"Matches: {results['total_matches']}"
    )


    # -----------------------------------------------------
    # QUERY 4
    # -----------------------------------------------------

    query = """
    I can compromise on parking.
    """

    results = find_properties_for_customer(
        query,
        conversation_history
    )

    print("\n==============================")
    print("QUERY 4")
    print("==============================")

    print(
        f"Matches: {results['total_matches']}"
    )


    # -----------------------------------------------------
    # SHOW COMPLETE CONVERSATION HISTORY
    # -----------------------------------------------------

    print("\n==============================")
    print("COMPLETE CONVERSATION HISTORY")
    print("==============================")


    for message in conversation_history:

        print("\n------------------------------")

        print(
            f"ROLE: {message['role']}"
        )

        print(
            f"CONTENT:\n{message['content']}"
        )