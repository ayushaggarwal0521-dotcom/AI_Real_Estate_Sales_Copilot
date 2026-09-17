from flask import Flask, request
import os
import requests
from dotenv import load_dotenv

from whatsapp_agent import (
    create_new_customer_state,
    handle_message
)
from property_images import get_property_images
from customer_manager import get_or_create_customer
load_dotenv()

app = Flask(__name__)


# ============================================================
# CONFIG
# ============================================================

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

GRAPH_API_URL = (
    f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
)
# This creates the API endpoint we use to send WhatsApp messages.

# ============================================================
# CUSTOMER STATES
# ============================================================

customer_states = {}
processed_messages = set()

# ============================================================
# WEBHOOK VERIFICATION
# ============================================================

@app.route("/webhook", methods=["GET"])
def verify_webhook():

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:

        print("Webhook verified successfully!")

        return challenge, 200

    print("Webhook verification failed.")

    return "Verification failed", 403


# ============================================================
# RECEIVE WHATSAPP MESSAGES
# ============================================================

@app.route("/webhook", methods=["POST"])
def receive_message():

    data = request.get_json()

    print("\n==============================")
    print("WHATSAPP WEBHOOK RECEIVED")
    print("==============================")

    print(data)

    try:

        # ----------------------------------------------------
        # EXTRACT WHATSAPP DATA
        # ----------------------------------------------------

        entry = data["entry"][0]

        changes = entry["changes"][0]

        value = changes["value"]

        messages = value.get("messages")

        if not messages:
            print("Ignoring webhook event without messages.")
            return {"status": "ignored"}, 200


        
        # ----------------------------------------------------
        # IGNORE EVENTS WITHOUT MESSAGES
        # ----------------------------------------------------

        message = messages[0]
        message_id = message["id"]
        if message_id in processed_messages:
            print("Duplicate message ignored.")
            return {"status": "duplicate"}, 200

        processed_messages.add(message_id)

# ----------------------------------------------------
# EXTRACT MESSAGE DATA
# ----------------------------------------------------

        

        sender = message["from"]

        message_type = message["type"]


        print(f"\nCUSTOMER PHONE: {sender}")
        print(f"MESSAGE TYPE: {message_type}")


        # ====================================================
        # GET / CREATE CUSTOMER STATE
        # ====================================================

        if sender not in customer_states:

            print("\nNEW CUSTOMER")

            customer_states[sender] = (
                create_new_customer_state()
            )

        state = customer_states[sender]
        customer_id = get_or_create_customer(
            sender
        )

        print(f"CRM CUSTOMER ID: {customer_id}")


        # ====================================================
        # TEXT MESSAGE
        # ====================================================

        if message_type == "text":

            user_message = message["text"]["body"]

            print(f"\nCUSTOMER: {user_message}")


            # ------------------------------------------------
            # SEND MESSAGE TO REAL ESTATE AGENT
            # ------------------------------------------------

            response = handle_message(
                state,
                user_message
            )


            print("\nAGENT RESPONSE:")
            print(response)


            # ------------------------------------------------
            # SEND RESPONSE BACK TO WHATSAPP
            # ------------------------------------------------

            send_agent_response(
                sender,
                response
            )


        # ====================================================
        # INTERACTIVE MESSAGE
        # ====================================================

        elif message_type == "interactive":

            interactive = message["interactive"]

            print("\nINTERACTIVE MESSAGE:")
            print(interactive)


            # ------------------------------------------------
            # BUTTON REPLY
            # ------------------------------------------------

            if interactive["type"] == "button_reply":

                button_id = (
                    interactive["button_reply"]["id"]
                )

                button_text = (
                    interactive["button_reply"]["title"]
                )

                print(
                    f"\nBUTTON ID: {button_id}"
                )

                print(
                    f"BUTTON TEXT: {button_text}"
                )


                # --------------------------------------------
                # SEND BUTTON TEXT TO AGENT
                # --------------------------------------------

                response = handle_message(
                    state,
                    button_text
                )


                print("\nAGENT RESPONSE:")
                print(response)


                # --------------------------------------------
                # SEND RESPONSE TO WHATSAPP
                # --------------------------------------------

                send_agent_response(
                    sender,
                    response
                )


            # ------------------------------------------------
            # LIST REPLY
            # ------------------------------------------------

            elif interactive["type"] == "list_reply":

                list_reply = (
                    interactive["list_reply"]
                )

                selected_id = (
                    list_reply["id"]
                )

                selected_title = (
                    list_reply["title"]
                )


                print(
                    f"\nLIST ID: {selected_id}"
                )

                print(
                    f"\nLIST TITLE: {selected_title}"
                )


                # --------------------------------------------
                # SEND LIST SELECTION TO AGENT
                # --------------------------------------------

                response = handle_message(
                    state,
                    selected_title
                )


                print("\nAGENT RESPONSE:")
                print(response)


                # --------------------------------------------
                # SEND RESPONSE TO WHATSAPP
                # --------------------------------------------

                send_agent_response(
                    sender,
                    response
                )


    except Exception as e:

        print("\n==============================")
        print("ERROR PROCESSING WEBHOOK")
        print("==============================")

        print(e)


    return "EVENT_RECEIVED", 200


# ============================================================
# SEND AGENT RESPONSE
# ============================================================

def send_agent_response(to, response):

    response_type = response.get("type")


    # ========================================================
    # NORMAL TEXT
    # ========================================================

    if response_type == "text":

        send_whatsapp_message(
            to,
            response.get("text", "")
        )


    # ========================================================
    # FREE TEXT PROMPT
    # ========================================================

    elif response_type == "free_text":

        send_whatsapp_message(
            to,
            response.get("text", "")
        )


    # ========================================================
    # BUTTON RESPONSE
    # ========================================================

    elif response_type == "buttons":

        text = response.get(
            "text",
            ""
        )

        buttons = response.get(
            "buttons",
            []
        )

        send_whatsapp_buttons(
            to,
            text,
            buttons
        )


    # ========================================================
    # PROPERTY RESULTS
    # ========================================================

    elif response_type == "property_results":

        send_property_results(
            to,
            response
        )


    # ========================================================
    # AI RESULTS
    # ========================================================

    elif response_type == "ai_results":

        send_ai_results(
            to,
            response
        )


    # ========================================================
    # UNKNOWN RESPONSE
    # ========================================================

    else:

        send_whatsapp_message(
            to,
            "Sorry, something went wrong."
        )


# ============================================================
# SEND WHATSAPP TEXT MESSAGE
# ============================================================

def send_whatsapp_message(to, message):

    headers = {

        "Authorization":
            f"Bearer {WHATSAPP_ACCESS_TOKEN}",

        "Content-Type":
            "application/json"
    }


    payload = {

        "messaging_product":
            "whatsapp",

        "to":
            to,

        "type":
            "text",

        "text": {

            "body":
                message
        }
    }


    response = requests.post(

        GRAPH_API_URL,

        headers=headers,

        json=payload
    )


    print("\nMETA RESPONSE:")
    print(response.status_code)
    print(response.text)


    return response

def send_whatsapp_image(to, image_url, caption=""):

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        }
    }

    response = requests.post(
        GRAPH_API_URL,
        headers=headers,
        json=payload
    )

    print("\nMETA IMAGE RESPONSE:")
    print(response.status_code)
    print(response.text)

    return response
# ============================================================
# SEND WHATSAPP BUTTONS
# ============================================================

def send_whatsapp_buttons(
    to,
    text,
    buttons
):

    # WhatsApp interactive messages support
    # a maximum of 3 reply buttons.

    buttons = buttons[:3]


    action_buttons = []


    for index, button in enumerate(buttons):

        action_buttons.append({

            "type":
                "reply",

            "reply": {

                "id":
                    f"button_{index}",

                "title":
                    button
            }
        })


    headers = {

        "Authorization":
            f"Bearer {WHATSAPP_ACCESS_TOKEN}",

        "Content-Type":
            "application/json"
    }


    payload = {

        "messaging_product":
            "whatsapp",

        "to":
            to,

        "type":
            "interactive",

        "interactive": {

            "type":
                "button",

            "body": {

                "text":
                    text
            },

            "action": {

                "buttons":
                    action_buttons
            }
        }
    }


    response = requests.post(

        GRAPH_API_URL,

        headers=headers,

        json=payload
    )


    print("\nMETA BUTTON RESPONSE:")
    print(response.status_code)
    print(response.text)


    return response


# ============================================================
# SEND PROPERTY RESULTS
# ============================================================

def send_property_results(
    to,
    response
):

    properties = response.get(
        "properties",
        []
    )


    if not properties:

        send_whatsapp_message(

            to,

            "I couldn't find matching properties right now."
        )

        return


    message_lines = []


    message_lines.append(
        f"🏠 I found {len(properties)} matching properties:\n"
    )


    for index, property_data in enumerate(
        properties[:5],
        start=1
    ):

        title = property_data.get(
            "title",
            "Property"
        )

        city = property_data.get(
            "city",
            ""
        )

        location = property_data.get(
            "location",
            ""
        )

        price = property_data.get(
            "price",
            0
        )

        bhk = property_data.get(
            "bhk",
            ""
        )


        # Convert price to crore/lakh style
        if isinstance(price, (int, float)):

            price_cr = price / 10000000

            price_text = (
                f"₹{price_cr:.2f} Cr"
            )

        else:

            price_text = str(price)


        message_lines.append(

            f"{index}. {title}\n"
            f"📍 {location}, {city}\n"
            f"🛏 {bhk} BHK\n"
            f"💰 {price_text}\n"
        )


    message_lines.append(
        "Tell me what you'd like to change or refine."
    )


    send_whatsapp_message(
        to,
        "\n".join(message_lines)
    )


# ============================================================
# SEND AI RESULTS
# ============================================================

def send_ai_results(
    to,
    response
):

    results = response.get(
        "results",
        []
    )


    if not results:

        send_whatsapp_message(

            to,

            "I couldn't find a strong match right now. "
            "Try changing your budget, location, or requirements."
        )

        return


    message_lines = []


    message_lines.append(
        "🏠 Here are the best matches I found:\n"
    )


    for index, result in enumerate(
        results[:5],
        start=1
    ):

        property_data = result.get(
            "property",
            result
        )


        property_id = property_data.get(
            "property_id",
            property_data.get(
                "id",
                "Unknown"
            )
        )
       

        title = property_data.get(
            "title",
            "Property"
        )
        images = get_property_images(property_id)

        if images:
            send_whatsapp_image(
                to,
                images[0],
                f"🏠 {title}"
            )

        city = property_data.get(
            "city",
            ""
        )

        location = property_data.get(
            "location",
            ""
        )

        price = property_data.get(
            "price",
            0
        )

        bhk = property_data.get(
            "bhk",
            ""
        )

        match_score = result.get(
            "match_score",
            ""
        )


        if isinstance(price, (int, float)):

            price_cr = price / 10000000

            price_text = (
                f"₹{price_cr:.2f} Cr"
            )

        else:

            price_text = str(price)


        score_text = ""

        if match_score != "":

            score_text = (
                f"🎯 Match: {match_score}/100\n"
            )


        message_lines.append(

            f"{index}. {title}\n"
            f"📍 {location}, {city}\n"
            f"🛏 {bhk} BHK\n"
            f"💰 {price_text}\n"
            f"{score_text}"
        )


    message_lines.append(
        "Want me to refine these further?"
    )


    send_whatsapp_message(
        to,
        "\n".join(message_lines)
    )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print(
        "Starting WhatsApp webhook server..."
    )

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True
    )