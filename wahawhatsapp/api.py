import frappe
import frappe.utils
import requests
import re
import json
import time
# from datetime import datetime
from frappe.utils import nowdate, add_days

@frappe.whitelist(allow_guest=True)
def waha_webhook():
    data = frappe.request.get_json()


    if data.get("event") != "message":
        return "OK"

    payload = data["payload"]
    sender = payload.get("from")
    text = payload.get("body").strip()

    # data = frappe.request.get_json()
    # debug_text = json.dumps(data, indent=2)
    # send_whatsapp(sender,debug_text)
    # return "OK"

    if sender != "916265064809@c.us":
        return "OK"
       
    session = frappe.get_all("user sessions", filters={"user": sender}, fields=["name", "state"])

    if not session:
        doc = frappe.get_doc({
            "doctype": "user sessions",
            "user": sender,
            "state": "start",
            "last_message": text
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Create Customer
        customer_name = sender.replace("@c.us", "")
        existing_customer = frappe.db.exists("Customer", customer_name)
        if not existing_customer:
            customer_doc = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer_name,
                "customer_group": "Individual",  # adjust as per your system
                "territory": "India"
            })
            customer_doc.insert(ignore_permissions=True)

        time.sleep(0.5)
        send_whatsapp(sender, "Hello Sir/Mam, Thanks for choosing *WhiffCulture* 🌟 .")#\nYour one stop Fragrance solution
        time.sleep(2)
        send_whatsapp(sender, "👋 Say goodbye to delays — We've made ordering simpler and faster; So you get what you need without the wait. ")
        time.sleep(2.5)
        send_whatsapp(sender, "You can start by typing the '*Name*' of fragrance you want. \nHappy to help 🥰")

        doc.state = "waiting_item_name"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return "OK"
    
    # Existing session
    session_doc = frappe.get_doc("user sessions", session[0].name)
    session_doc.last_message = text
    session_doc.save(ignore_permissions=True)

    if text.lower() == "restart":
        send_whatsapp(sender, "Thank you for choosing *WhiffCulture*! 🌟")
        time.sleep(1.5)
        send_whatsapp(sender, "Start a new enquiry anytime, You can directly type the *'Name'* of fragrance you want! 🔁")
        session_doc.cart = None  
        session_doc.cart_total = 0
        session_doc.state= "waiting_item_name"
        session_doc.save(ignore_permissions=True)

        return "OK"
    
    if text.lower() == "delete":
        frappe.delete_doc("user sessions", session_doc.name, ignore_permissions=True)
        send_whatsapp(sender, "Your session has been deleted.🗑️")
        return "OK"
    
    if text.lower() == "checkout":
        if not session_doc.cart:
            send_whatsapp(sender, "🛒 Your cart is empty!")
            return "OK"

        cart = json.loads(session_doc.cart)
        summary = "🛍️ *Your Cart:*\n\n"
        total = 0
        for idx, item in enumerate(cart, 1):
            subtotal = item["qty"] * item["price"]
            summary += f"{idx}. {item['item_name']} x{item['qty']} = ₹{subtotal}\n"
            total += subtotal

        summary += f"\n💰 *Total: ₹{total}*\n\nType *'Place order'* to proceed to shipping."

        session_doc.state = "place_order"  # Continue from normal flow
        session_doc.save(ignore_permissions=True)

        send_whatsapp(sender, summary)
        return "OK"

    if text.lower()=="cart":
            if not session_doc.cart:
                send_whatsapp(sender, "🛒 Your cart is empty!")
                time.sleep(1.5)
                send_whatsapp(sender, "You can add in by typing the *'Name'* of fragrance you want!")
                session_doc.state = "waiting_item_name"  
                session_doc.save(ignore_permissions=True)
                return "OK"
            
            cart =json.loads(session_doc.cart)
            summary =  "🛍️ *Your Cart:*\n\n"
            total =0

            for idx,item in enumerate(cart,1):
                subtotal=item["qty"]*item["price"]
                summary+= f"{idx}. {item['item_name']} x{item['qty']} = ₹{subtotal}\n"
                total += subtotal
            
            summary += f"\n💰 *Total: ₹{total}*\n\nType *Place order* to proceed to shipping."
            session_doc.state = "waiting_item_name"  
            session_doc.save(ignore_permissions=True)
            send_whatsapp(sender, summary)
            return "OK"
    
    if text.lower()=="place order":
        session_doc.state= "place_order"
        session_doc.save(ignore_permissions=True)


    # State machine
    if session_doc.state == "start":

        # time.sleep(0.5)
        # send_whatsapp(sender, "Heyyy, Thanks for choosing Luxir - Your one stop perfume solution. ")
        time.sleep(2)
        send_whatsapp(sender, "👋 Say goodbye to delays — We've made ordering simpler and faster, so you get what you need without the wait. 🥷")
        time.sleep(2.5)
        send_whatsapp(sender, "You can directly type the *'Name'* of fragrance you want \nHappy to help. 🥰")
        session_doc.state = "waiting_item_name"
        session_doc.save(ignore_permissions=True)
        # return "OK"

    elif session_doc.state == "waiting_item_name":
        items = frappe.get_all(
            "Item",
            filters={"item_name": ["like", f"%{text}%"]},
            fields=["item_code", "item_name", "item_group"],
            order_by="item_name asc",
            # limit=5
        )
        session_doc.payment_status = "unpaid"


        if not items:
            send_whatsapp(sender, "❤️‍🩹 Sorry, I can't find this fragrance currently in the inventory. \n\nNeed help with some other perfumes? ")
            time.sleep(1.5)
            send_whatsapp(sender, "You can directly type the *'Name'* of fragrance you want 😊")
            return "OK"

        if len(items) == 1:
            # Only one match, proceed as before
            item = items[0]
            price = frappe.db.get_value("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"}, "price_list_rate")
            if price:
                session_doc.perfume_name = item.item_name
                session_doc.state = "waiting_book"
                session_doc.save(ignore_permissions=True)
                reply = f"☑️ Yeah!\n*{item.item_name}* - {item.item_group}\nIn Stock!"
                send_whatsapp(sender, reply)
                time.sleep(1)
                reply = f"*₹{price}* (inclusive of shipping)"
                send_whatsapp(sender, reply)
                reply = "You can reply '*Add*' to order 1 piece, or '*Add 2*' for two pieces, and so on.\n\n Or type: \n'*Restart*' for a fresh enquiry."
                time.sleep(2)
                send_whatsapp(sender, reply)
                # reply = "Type 'Restart' to make a fresh enquiry. 😊"
                # time.sleep(2)
                # send_whatsapp(sender, reply)
            else:
                send_whatsapp(sender, f"{item.item_name} is available, but price is not set.")
        else:
            # Multiple items found, list them
            options_text = ""
            send_whatsapp(sender, "😮‍💨 Woof!! Looks like I have found multiple perfumes matching your enquiry:")
            time.sleep(1.5)
            for idx, it in enumerate(items, start=1):
                options_text += f"*{idx}. {it.item_name}* - {it.item_group}\n"
            options_text += "\nPlease reply with the number of your choice (e.g., 1, 2, 3...)."

            items_to_save = []

            for it in items:
                items_to_save.append({
                    "item_code": it.item_code,
                    "item_name": it.item_name,
                    "item_group": it.item_group
                })

            # Save items temporarily in session (as JSON string)
            # items_to_save = [dict(it) for it in items]
            session_doc.temp_items = json.dumps(items_to_save)
            session_doc.state = "waiting_selection"
            session_doc.save(ignore_permissions=True)
            send_whatsapp(sender, options_text)

    elif session_doc.state == "waiting_selection":
        try:
            selected_index = int(text.strip()) - 1
            items_list = json.loads(session_doc.temp_items)
            selected_item = items_list[selected_index]
        except:
            send_whatsapp(sender, "Invalid selection. Please reply with a valid number from the list.")
            return "OK"

        price = frappe.db.get_value("Item Price", {"item_code": selected_item["item_code"], "price_list": "Standard Selling"}, "price_list_rate")
        if price:
            session_doc.perfume_name = selected_item["item_name"]
            session_doc.state = "waiting_book"
            session_doc.save(ignore_permissions=True)

            reply = f"☑️ Yeah!\n*{selected_item["item_name"]}* - {selected_item["item_group"]}\nIn Stock!"
            send_whatsapp(sender, reply)
            time.sleep(1)
            reply = f"*₹ {price}* (inclusive of shipping)"
            send_whatsapp(sender, reply)
            reply = "You can reply '*Add*' to order 1 piece, or '*Add 2*' for two pieces, and so on.\n\nOr type: \n'*Restart*' for a fresh enquiry. \n *'Cart'* to view your cart."
            time.sleep(2)
            send_whatsapp(sender, reply)
            # reply = "Type 'Restart' to make a fresh enquiry. 😊"
            # time.sleep(2)
            # send_whatsapp(sender, reply)
        else:
            send_whatsapp(sender, f"{selected_item['item_name']} is available, but price is not set.")

    elif session_doc.state == "waiting_book":
        match = re.match(r"add\s*(\d*)", text.lower())
        # match1 = re.match(r"restart\s*(\d*)", text.lower())
        if match:
            qty = match.group(1)
            qty = int(qty) if qty else 1
            # session_doc.quantity = qty
            # session_doc.state = "waiting_name"
            # session_doc.save(ignore_permissions=True)

            # Add to cart
            item_code = frappe.db.get_value("Item", {"item_name": session_doc.perfume_name}, "item_code")
            price = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": "Standard Selling"}, "price_list_rate")

            # Load existing cart or start new
            cart = json.loads(session_doc.cart) if session_doc.cart else []

            # Add this item
            cart.append({
                "item_code": item_code,
                "item_name": session_doc.perfume_name,
                "price": price,
                "qty": qty
            })

            # Save back to session
            session_doc.cart = json.dumps(cart)
            session_doc.state = "waiting_item_name"  # Let user keep shopping
            session_doc.save(ignore_permissions=True)
            send_whatsapp(sender, f"🛒 *{session_doc.perfume_name}* x{qty} added to your cart.\n\nType the *'Name'* of another perfume to continue shopping;\n Or type:\n*'Checkout'* to finish your order.")
            # time.sleep(1)

   
        else:
            send_whatsapp(sender, "Please type '*Add*' or '*Add 2*' for 2 quantities.")
            time.sleep(2)
            send_whatsapp(sender, "Or you can type '*Restart*' for a fresh enquiry.🔁")

    elif session_doc.state == "place_order":
        # session_doc.payment_status = "unpaid"
        session_doc.state = "waiting_name"

        session_doc.save(ignore_permissions=True)
        send_whatsapp(sender, "Payment link/QR is generated!🔗")
        time.sleep(2)
        send_whatsapp(sender, "Payment is received successfully!✅")
        time.sleep(2)
        send_whatsapp(sender, "🤝 Proceed by adding your SHIPPING DETAILS carefully")
        time.sleep(1)
        send_whatsapp(sender, "Please enter Receiver's *FULL* *NAME* :")

        # time0= time.time()
        # time1= time0 +60

        # while time0<=time1:
            # if session_doc.payment_status == "paid":
                # session_doc.state = "waiting_name"
                # session_doc.save(ignore_permissions=True)

                        # send_whatsapp(sender, "Payment is received successfully!☑️")
                        # time.sleep(2)
                        # send_whatsapp(sender, "🤝 Proceed by adding your SHIPPING DETAILS carefully")
                        # time.sleep(1)
                        # send_whatsapp(sender, "Please enter Receiver's *FULL* *NAME* :")
                # break
            # time.sleep(1)
        # return "OK"
                   
    elif session_doc.state== "confirmation":
        if session_doc.payment_status== "paid":
            session_doc.state = "waiting_name"
            session_doc.save(ignore_permissions=True)

            send_whatsapp(sender, "Payment is received successfully!☑️")
            time.sleep(2)
            send_whatsapp(sender, "🤝 Proceed by adding your SHIPPING DETAILS carefully")
            time.sleep(1)
            send_whatsapp(sender, "Please enter Receiver's *FULL* *NAME* :")

    elif session_doc.state == "waiting_name":
        session_doc.customer_name = text
        session_doc.state = "waiting_address"
        session_doc.save(ignore_permissions=True)
        time.sleep(1)
        send_whatsapp(sender, "Please enter Receiver's full *Address* with *Pincode* :")

    elif session_doc.state == "waiting_address":
        session_doc.address = text
        session_doc.state = "waiting_phone"
        session_doc.save(ignore_permissions=True)
        time.sleep(1)
        send_whatsapp(sender, "Lastly enter Receiver's *Phone Number*")

    elif session_doc.state == "waiting_phone":
        session_doc.phone_no = text
        # session_doc.state = "completed"
        # session_doc.save(ignore_permissions=True)
        time.sleep(1)
        send_whatsapp(sender, "✅ Thank you! Your Order has been confirmed!!")
        time.sleep(1.5)
        send_whatsapp(sender, "🫡 We will share your tracking ID by tomorrow EOD.")
        time.sleep(1)
        send_whatsapp(sender, "❤️Thanks for choosing *WhiffCulture* .") #Your one stop Perfume Solution
        # session_doc.cart = None  # or "" if that's your default
        # session_doc.cart_total = 0

        session_doc.state = "completed"
        session_doc.save(ignore_permissions=True)
        # return "OK"

        # return "OK"

        # session_doc.state = "create_order"
        # session_doc.save(ignore_permissions=True)


    # elif session_doc.state == "create_order":

    #     try:
    #         send_whatsapp(sender, "inside try block")
    #         customer_name = session_doc.user.replace("@c.us", "")
    #         item = frappe.db.get_value("Item", {"item_name": session_doc.perfume_name}, "item_code")
    #         price = frappe.db.get_value("Item Price", {"item_code": item, "price_list": "Standard Selling"}, "price_list_rate")
    #         address_doc = frappe.get_doc({
    #                 "doctype": "Address",
    #                 "address_title": session_doc.customer_name,
    #                 "address_line1": session_doc.address,
    #                 "city": session_doc.address,
    #                 "country": "India",
    #                 "phone": session_doc.phone_number,
    #                 "links": [{
    #                     "link_doctype": "Customer",
    #                     "link_name": customer_name
    #                 }]
    #             })
    #         address_doc.insert(ignore_permissions=True)
    #         # frappe.db.commit()

    #         send_whatsapp(sender, "outside address")
    #         sales_order = frappe.get_doc({
    #                 "doctype": "Sales Order",
    #                 "customer": customer_name,
    #                 "delivery_date": frappe.utils.add_days(frappe.utils.nowdate(),5),
    #                 "items": [
    #                     {
    #                         "item_code": item,
    #                         "qty": session_doc.quantity,
    #                         "rate": price
    #                     }
    #                 ],
    #                 "shipping_address_name": address_doc.name
    #             })
    #         sales_order.insert(ignore_permissions=True)
    #         frappe.db.commit()

    #         send_whatsapp(sender, "✅ Thank you! Your Sales Order has been created successfully.")
    #         time.sleep(1)
    #         send_whatsapp(sender, "We will share your tracking ID by tomorrow EOD.")
    #         time.sleep(1)
    #         send_whatsapp(sender, "Thanks for choosing Luxir! Your one stop Perfume Solution.")
    #         session_doc.state = "waiting_phone"
    #         session_doc.save(ignore_permissions=True)

    #     except Exception as e:
    #         # frappe.log_error(frappe.get_traceback(), "Sales Order Creation Failed")
    #         send_whatsapp(sender, "⚠️ Oops! Something went wrong while creating your order. Please contact support.")


    elif session_doc.state == "completed":
        time.sleep(1)
        send_whatsapp(sender, "Want to explore more fragrances? \nType a perfume name to start a new order again. 🔁")
        session_doc.state = "waiting_item_name"
        session_doc.save(ignore_permissions=True)
        return "OK"

def send_whatsapp(chat_id, message):
    # frappe.log_error("helu", chat_id)
    # frappe.log_error("helu", message)
    url = "https://luxir.in/api/sendText"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Api-Key": "admin"
    }
    data = {
        "chatId": "916265064809@c.us",
        "text": message,
        "session": "default"
    }
    
    response = requests.post(url, json=data, headers=headers)
    frappe.log_error("WAHA sendText response", response.text)






