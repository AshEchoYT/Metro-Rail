import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
import random
import time
import re

st.set_page_config(
    page_title="Chennai Metro Ticket Booking",
    page_icon="🚇",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    .stApp {
        background-color: #f5f9ff;
    }
    .header {
        color: #003366;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .ticket-card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    .payment-form {
        background-color: #f0f7ff;
        padding: 1.5rem;
        border-radius: 10px;
    }
    .success-message {
        background-color: #e6f7ee;
        color: #006633;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #ffebee;
        color: #c62828;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .metro-primary {
        background-color: #003366 !important;
        color: white !important;
    }
    .metro-secondary {
        background-color: #0066cc !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

stations = {
    "Chennai Central": 0,
    "Park Town": 2,
    "Egmore": 4,
    "Kilpauk": 6,
    "Anna Nagar": 9,
    "Koyambedu": 12,
    "Vadapalani": 15,
    "Ashok Nagar": 18,
    "Guindy": 21,
    "Airport": 25
}

ticket_types = {
    "Single Journey": 1.0,
    "Return Journey": 1.8,
    "Day Pass": 3.0
}

def calculate_fare(from_station, to_station, ticket_type):
    distance = abs(stations[to_station] - stations[from_station])
    base_fare = 0
    if distance <= 2: base_fare = 10
    elif distance <= 5: base_fare = 20
    elif distance <= 10: base_fare = 30
    elif distance <= 15: base_fare = 40
    else: base_fare = 50
    return round(base_fare * ticket_types[ticket_type])

def get_next_trains(direction):
    now = datetime.now()
    if direction == "northbound":
        return [(now + timedelta(minutes=i*8)).strftime("%H:%M") for i in range(1,6)]
    else:
        return [(now + timedelta(minutes=i*10)).strftime("%H:%M") for i in range(1,6)]

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#003366", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    return base64.b64encode(byte_im).decode()

def process_payment(amount, card_details):
    time.sleep(2)
    if not card_details["number"].replace(" ", "").isdigit() or len(card_details["number"].replace(" ", "")) != 16:
        return False, "Invalid card number"
    current_year = datetime.now().year
    current_month = datetime.now().month
    if (card_details["expiry_year"] < current_year) or \
       (card_details["expiry_year"] == current_year and card_details["expiry_month"] < current_month):
        return False, "Card expired"
    if len(card_details["cvv"]) != 3 or not card_details["cvv"].isdigit():
        return False, "Invalid CVV"
    if random.random() < 0.85:
        return True, f"PMT{random.randint(100000, 999999)}"
    else:
        failure_reasons = [
            "Insufficient funds",
            "Bank declined transaction",
            "Network error",
            "Card limit exceeded"
        ]
        return False, random.choice(failure_reasons)

if "tickets" not in st.session_state:
    st.session_state.tickets = []

if "current_ticket" not in st.session_state:
    st.session_state.current_ticket = None

if "payment_attempted" not in st.session_state:
    st.session_state.payment_attempted = False

def show_home_page():
    st.markdown("<h1 class='header'>🚇 Chennai Metro Ticket Booking</h1>", unsafe_allow_html=True)
    
    with st.form("ticket_form"):
        st.subheader("Journey Details")
        col1, col2 = st.columns(2)
        with col1:
            from_station = st.selectbox("From", list(stations.keys()))
        with col2:
            to_station = st.selectbox("To", list(stations.keys()))
        ticket_type = st.radio("Ticket Type", list(ticket_types.keys()), horizontal=True)
        passenger_count = st.number_input("Passengers", min_value=1, max_value=10, value=1)
        
        st.subheader("Passenger Details")
        passenger_names = []
        passenger_phones = []
        
        for i in range(passenger_count):
            with st.expander(f"Passenger {i+1} Details", expanded=(i==0)):
                col_name, col_phone = st.columns(2)
                with col_name:
                    name = st.text_input(f"Full Name {i+1}", key=f"name_{i}")
                with col_phone:
                    phone = st.text_input(f"Phone Number {i+1}", key=f"phone_{i}")
                passenger_names.append(name)
                passenger_phones.append(phone)
        
        submitted = st.form_submit_button("Calculate Fare", type="primary")
    
    if submitted:
        validation_errors = []
        if from_station == to_station:
            validation_errors.append("Departure and arrival stations cannot be the same.")
        for i in range(passenger_count):
            if not passenger_names[i].strip():
                validation_errors.append(f"Passenger {i+1} name cannot be empty")
            if not re.match(r'^[0-9]{10}$', passenger_phones[i]):
                validation_errors.append(f"Passenger {i+1} phone number must be 10 digits")
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            fare = calculate_fare(from_station, to_station, ticket_type)
            total_fare = fare * passenger_count
            st.session_state.current_ticket = {
                "from": from_station,
                "to": to_station,
                "type": ticket_type,
                "passenger_count": passenger_count,
                "passenger_names": passenger_names,
                "passenger_phones": passenger_phones,
                "fare": fare,
                "total": total_fare,
                "direction": "northbound" if stations[from_station] < stations[to_station] else "southbound"
            }
            
            with st.container():
                st.markdown("<div class='ticket-card'>", unsafe_allow_html=True)
                st.subheader("Fare Summary")
                st.write(f"**From:** {from_station}")
                st.write(f"**To:** {to_station}")
                st.write(f"**Ticket Type:** {ticket_type}")
                st.write(f"**Passengers:** {passenger_count}")
                with st.expander("View Passenger Details"):
                    for i in range(passenger_count):
                        st.write(f"**Passenger {i+1}:** {passenger_names[i]}")
                        st.write(f"**Phone:** {passenger_phones[i]}")
                        st.write("---")
                st.write(f"**Fare per passenger:** ₹{fare}")
                st.write(f"**Total Fare:** ₹{total_fare}")
                st.markdown("</div>", unsafe_allow_html=True)
                st.write("Next available trains:")
                st.write(", ".join(get_next_trains(st.session_state.current_ticket["direction"])))
                st.button("Proceed to Payment", type="primary", key="proceed_payment")

def show_payment_page():
    if not st.session_state.current_ticket:
        st.warning("Please select a ticket first.")
        return
    
    st.markdown("<h1 class='header'>💳 Payment</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='ticket-card'>", unsafe_allow_html=True)
        st.subheader("Payment Summary")
        st.write(f"**From:** {st.session_state.current_ticket['from']}")
        st.write(f"**To:** {st.session_state.current_ticket['to']}")
        st.write(f"**Total Amount:** ₹{st.session_state.current_ticket['total']}")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with st.form("payment_form"):
        st.subheader("Card Details")
        card_name = st.text_input("Cardholder Name")
        col1, col2 = st.columns([3,1])
        with col1:
            card_number = st.text_input("Card Number", placeholder="1234 5678 9012 3456")
        with col2:
            card_type = st.selectbox("Card Type", ["Visa", "MasterCard", "Rupay"])
        col3, col4 = st.columns(2)
        with col3:
            expiry_month = st.selectbox("Expiry Month", range(1,13), format_func=lambda x: f"{x:02d}")
        with col4:
            expiry_year = st.selectbox("Expiry Year", range(datetime.now().year, datetime.now().year + 10))
        cvv = st.text_input("CVV", max_chars=3, type="password")
        submitted = st.form_submit_button("Pay Now", type="primary")
        
        if submitted:
            card_details = {
                "name": card_name,
                "number": card_number,
                "type": card_type,
                "expiry_month": expiry_month,
                "expiry_year": expiry_year,
                "cvv": cvv
            }
            st.session_state.payment_attempted = True
            with st.spinner("Processing payment..."):
                success, message = process_payment(
                    st.session_state.current_ticket['total'],
                    card_details
                )
                if success:
                    st.session_state.payment_status = "success"
                    st.session_state.payment_id = message
                    ticket_data = {
                        "ticket_id": f"CMRL-{random.randint(1000,9999)}-{datetime.now().strftime('%Y%m%d')}",
                        "journey": f"{st.session_state.current_ticket['from']} → {st.session_state.current_ticket['to']}",
                        "type": st.session_state.current_ticket['type'],
                        "passengers": st.session_state.current_ticket['passenger_count'],
                        "passenger_names": st.session_state.current_ticket['passenger_names'],
                        "passenger_phones": st.session_state.current_ticket['passenger_phones'],
                        "fare": st.session_state.current_ticket['total'],
                        "valid_on": datetime.now().strftime("%d %b %Y"),
                        "payment_id": message,
                        "qr_data": generate_qr_code(f"CMRL|{st.session_state.current_ticket['from']}|{st.session_state.current_ticket['to']}|{st.session_state.current_ticket['type']}|{message}")
                    }
                    st.session_state.tickets.append(ticket_data)
                else:
                    st.session_state.payment_status = "failed"
                    st.session_state.payment_message = message
    
    if st.session_state.get('payment_attempted', False):
        if st.session_state.get('payment_status') == "success":
            st.markdown(f"""
            <div class='success-message'>
                <h3>🎉 Payment Successful!</h3>
                <p>Payment ID: {st.session_state.payment_id}</p>
                <p>Your ticket has been booked successfully.</p>
            </div>
            """, unsafe_allow_html=True)
            latest_ticket = st.session_state.tickets[-1]
            st.image(f"data:image/png;base64,{latest_ticket['qr_data']}", width=200)
            st.download_button(
                label="Download Ticket",
                data=BytesIO(base64.b64decode(latest_ticket['qr_data'])),
                file_name=f"cmrl_ticket_{latest_ticket['ticket_id']}.png",
                mime="image/png"
            )
            if st.button("Book Another Ticket"):
                st.session_state.current_ticket = None
                st.session_state.payment_attempted = False
                st.rerun()
        elif st.session_state.get('payment_status') == "failed":
            st.markdown(f"""
            <div class='error-message'>
                <h3>❌ Payment Failed</h3>
                <p>Reason: {st.session_state.payment_message}</p>
                <p>Please try again or use a different payment method.</p>
            </div>
            """, unsafe_allow_html=True)

def show_my_tickets_page():
    st.markdown("<h1 class='header'>🎫 My Tickets</h1>", unsafe_allow_html=True)
    if not st.session_state.tickets:
        st.info("You haven't booked any tickets yet.")
        return
    for ticket in reversed(st.session_state.tickets):
        with st.container():
            st.markdown("<div class='ticket-card'>", unsafe_allow_html=True)
            st.write(f"**Ticket ID:** {ticket['ticket_id']}")
            st.write(f"**Journey:** {ticket['journey']}")
            st.write(f"**Type:** {ticket['type']}")
            st.write(f"**Passengers:** {ticket['passengers']}")
            with st.expander("View Passenger Details"):
                for i in range(ticket['passengers']):
                    st.write(f"**Passenger {i+1}:** {ticket['passenger_names'][i]}")
                    st.write(f"**Phone:** {ticket['passenger_phones'][i]}")
                    st.write("---")
            st.write(f"**Fare:** ₹{ticket['fare']}")
            st.write(f"**Valid on:** {ticket['valid_on']}")
            st.write(f"**Payment ID:** {ticket['payment_id']}")
            col1, col2 = st.columns([1,2])
            with col1:
                st.image(f"data:image/png;base64,{ticket['qr_data']}", width=120)
            with col2:
                st.download_button(
                    label="Download Ticket",
                    data=BytesIO(base64.b64decode(ticket['qr_data'])),
                    file_name=f"cmrl_ticket_{ticket['ticket_id']}.png",
                    mime="image/png",
                    key=f"dl_{ticket['ticket_id']}"
                )
            st.markdown("</div>", unsafe_allow_html=True)

def show_about_page():
    st.markdown("<h1 class='header'>ℹ️ About</h1>", unsafe_allow_html=True)
    st.markdown("""
    ### Chennai Metro Rail Ticket Booking System
    This is a demonstration application for booking metro tickets with a simulated payment gateway.
    **Features:**
    - Real-time fare calculation based on distance
    - Multiple ticket types (Single, Return, Day Pass)
    - Passenger details collection
    - Simulated payment processing
    - QR code ticket generation
    - Ticket history and download
    **Note:** This is a demo application. No real payments are processed.
    """)
    st.markdown("---")
    st.write("Built with ❤️ using Streamlit")

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "My Tickets", "About"])
    if page == "Home":
        show_home_page()
        if st.session_state.current_ticket:
            show_payment_page()
    elif page == "My Tickets":
        show_my_tickets_page()
    elif page == "About":
        show_about_page()

if __name__ == "__main__":
    main()