from fyers_apiv3 import fyersModel
from dhanhq import dhanhq
import threading
import time
import webbrowser
import requests
import re

# -----------------------------------------
# YOUR FYERS APP CREDENTIALS
# -----------------------------------------

fyers_client_id = "H7MGGNP0W6-100"                       ## Client_id here refers to APP_ID of the created app
fyers_secret_key = "PHIAF03SIW"                          ## app_secret key which you got after creating the app 
grant_type = "authorization_code"                  ## The grant_type always has to be "authorization_code"
response_type = "code"                             ## The response_type always has to be "code"
state = "sample"   
redirect_uri = "https://fyers-l82t.onrender.com/callback"   # IMPORTANT

# -----------------------------------------
# YOUR DHAN APP CREDENTIALS
# -----------------------------------------

dhan_client_id = "1101138021"            # TODO: Replace with your Dhan client ID (from Profile)
dhan_api_key = "9daa8f1e"                # TODO: Replace with your Dhan API Key
dhan_api_secret = "41ab9c4b-f71a-4c2c-a584-60a9adb527b9"          # TODO: Replace with your Dhan API Secret
dhan_access_token = None                           # Will be obtained via OAuth flow
dhan_redirect_uri = "https://fyers-l82t.onrender.com/callback/dhan"  # Dhan callback URL



# =========================
# Global variable to store auth_code
# =========================
auth_data = {}

def poll_external_url_for_auth_code():
    """Poll the API endpoint to get a fresh auth code"""
    max_attempts = 300  # Wait up to 5 minutes
    attempt = 0
    
    # Use the API endpoint instead of the callback page
    api_url = redirect_uri.replace('/callback', '/get-auth-code')
    
    print(f"Polling API endpoint: {api_url}")
    print("Waiting for fresh auth code to be stored...")
    
    while attempt < max_attempts:
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("auth_code"):
                    auth_code = data["auth_code"]
                    code_age = data.get("code_age_seconds", 0)
                    auth_data["auth_code"] = auth_code
                    print(f"\n✅ Fresh auth code retrieved (age: {int(code_age)}s): {auth_code[:50]}...")
                    return auth_code
            elif response.status_code == 404:
                # No auth code yet, keep waiting
                if attempt % 10 == 0:
                    print(f"  Attempt {attempt}: Waiting for login to complete...")
            elif response.status_code == 410:
                # Code expired, need new login
                data = response.json()
                print(f"\n⚠️  {data.get('message', 'Auth code expired')}")
                print("Please complete a fresh login in the browser...")
                if attempt % 10 == 0:
                    print(f"  Attempt {attempt}: Waiting for fresh login...")
            else:
                if attempt % 10 == 0:
                    print(f"  Attempt {attempt}: Unexpected response: {response.status_code}")
                    
        except requests.exceptions.RequestException as e:
            if attempt % 10 == 0:
                print(f"  Attempt {attempt}: Connection error - {e}")
        except Exception as e:
            if attempt % 10 == 0:
                print(f"  Attempt {attempt}: Error - {e}")
        
        attempt += 1
        time.sleep(1)
    
    return None

def clear_stored_auth_code():
    """Clear the auth code from the service after successful use"""
    try:
        clear_url = redirect_uri.replace('/callback', '/clear-auth-code')
        response = requests.get(clear_url, timeout=5)
        if response.status_code == 200:
            print("✅ Cleared used auth code from service")
    except Exception as e:
        print(f"⚠️  Warning: Could not clear auth code: {e}")

# =========================
# FYERS Session and Auth Flow
# =========================
# Initialize session model
appSession = fyersModel.SessionModel(
    client_id=fyers_client_id,
    secret_key=fyers_secret_key,
    redirect_uri=redirect_uri,
    response_type=response_type,
    state=state,
    grant_type=grant_type
)

# Generate login URL
login_url = appSession.generate_authcode()
print("Opening browser for FYERS login...")
webbrowser.open(login_url, new=1)

# Wait for auth_code by polling the external URL
print("Waiting for auth_code from external URL...")
print(f"After login, Fyers will redirect to: {redirect_uri}")
print("Make sure you complete the login in the browser...\n")
auth_code = poll_external_url_for_auth_code()

if not auth_code:
    print("\n❌ Failed to retrieve auth code after 5 minutes.")
    print("Please ensure:")
    print("1. You completed the Fyers login in the browser")
    print("2. The external service is running and accessible")
    print("3. The service has been updated with the new code")
    exit(1)

# Generate access token
print("\nGenerating access token...")
appSession.set_token(auth_code)
response = appSession.generate_token()

try:
    access_token = response["access_token"]
    print(f"\n✅ Access token generated successfully!")
    print(f"Access Token: {access_token}")
    print("\n" + "="*60)
    print("SUCCESS! You can now use this access token for API calls.")
    print("="*60)
    
    # Clear the used auth code from service to prevent reuse
    clear_stored_auth_code()
    
except Exception as e:
    print(f"\n❌ Error generating access token: {e}")
    print(f"Response: {response}")
    
    # If it's an "invalid auth code" error, clear it and suggest fresh login
    if isinstance(response, dict) and response.get("message") == "invalid auth code":
        print("\n⚠️  This auth code was already used or expired.")
        print("Clearing it from service. Please run the script again for a fresh login.")
        clear_stored_auth_code()
    
    exit(1)


fyers = fyersModel.FyersModel(token=access_token,is_async=False,client_id=fyers_client_id,log_path="")

# =========================
# DHAN AUTHENTICATION FLOW - Function Definitions
# =========================

def poll_dhan_token_id():
    """Poll the API endpoint to get Dhan tokenId"""
    max_attempts = 300  # Wait up to 5 minutes
    attempt = 0
    
    # Yes, you remembered right! The endpoint for Dhan tokenId polling is handled via '/get-dhan-token', 
    # but the Dhan login POST/redirect hits '/callback/dhan', 
    # so for polling you want '/get-dhan-token', not '/callback/dhan'.
    api_url = redirect_uri.replace('/callback', '/get-dhan-token')
    
    print(f"Polling Dhan API endpoint: {api_url}")
    print("Waiting for Dhan tokenId to be stored...")
    
    while attempt < max_attempts:
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("token_id"):
                    token_id = data["token_id"]
                    code_age = data.get("code_age_seconds", 0)
                    print(f"\n✅ Dhan tokenId retrieved (age: {int(code_age)}s): {token_id[:50]}...")
                    return token_id
            elif response.status_code == 404:
                if attempt % 10 == 0:
                    print(f"  Attempt {attempt}: Waiting for Dhan login to complete...")
            elif response.status_code == 410:
                data = response.json()
                print(f"\n⚠️  {data.get('message', 'Dhan tokenId expired')}")
                print("Please complete a fresh Dhan login in the browser...")
                if attempt % 10 == 0:
                    print(f"  Attempt {attempt}: Waiting for fresh Dhan login...")
            else:
                if attempt % 10 == 0:
                    print(f"  Attempt {attempt}: Unexpected response: {response.status_code}")
                    
        except requests.exceptions.RequestException as e:
            if attempt % 10 == 0:
                print(f"  Attempt {attempt}: Connection error - {e}")
        except Exception as e:
            if attempt % 10 == 0:
                print(f"  Attempt {attempt}: Error - {e}")
        
        attempt += 1
        time.sleep(1)
    
    return None

def generate_dhan_consent():
    """
    STEP 1: Generate Consent
    Creates a consent session and returns consentAppId for browser login.
    Reference: https://dhanhq.co/docs/v2/authentication/
    """
    try:
        # STEP 1: Generate Consent
        consent_url = f"https://auth.dhan.co/app/generate-consent?client_id={dhan_client_id}"
        
        headers = {
            "app_id": dhan_api_key,
            "app_secret": dhan_api_secret
        }
        
        print("STEP 1: Generating Dhan consent...")
        response = requests.post(consent_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("consentAppId"):
                consent_app_id = data["consentAppId"]
                print(f"✅ Consent generated! consentAppId: {consent_app_id}")
                return consent_app_id
            else:
                print(f"❌ Error: Invalid response from consent API: {data}")
                return None
        else:
            print(f"❌ Error generating consent: Status {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating Dhan consent: {e}")
        import traceback
        traceback.print_exc()
        return None

def open_dhan_browser_login(consent_app_id):
    """
    STEP 2: Browser based login
    Opens browser for user to login. User will be redirected to callback URL with tokenId.
    Reference: https://dhanhq.co/docs/v2/authentication/
    """
    login_url = f"https://auth.dhan.co/login/consentApp-login?consentAppId={consent_app_id}"
    
    print(f"\nSTEP 2: Opening browser for Dhan login...")
    print(f"Login URL: {login_url}")
    print("Please complete the login in the browser...")
    
    webbrowser.open(login_url, new=1)
    return True

def get_dhan_access_token(token_id):
    """
    STEP 3: Consume Consent
    Exchange Dhan tokenId for access_token using Dhan API.
    Reference: https://dhanhq.co/docs/v2/authentication/
    """
    try:
        # STEP 3: Consume Consent - GET request with tokenId as query parameter
        consume_url = f"https://auth.dhan.co/app/consumeApp-consent?tokenId={token_id}"
        
        headers = {
            "app_id": dhan_api_key,
            "app_secret": dhan_api_secret
        }
        
        print(f"\nSTEP 3: Exchanging Dhan tokenId for access_token...")
        response = requests.get(consume_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("accessToken"):
                access_token = data["accessToken"]
                dhan_client_id_from_response = data.get("dhanClientId")
                expiry_time = data.get("expiryTime")
                
                print(f"✅ Dhan access_token obtained successfully!")
                print(f"   Client ID: {dhan_client_id_from_response}")
                print(f"   Expiry: {expiry_time}")
                
                # Update dhan_client_id if we got it from response
                global dhan_client_id
                if dhan_client_id_from_response:
                    dhan_client_id = dhan_client_id_from_response
                
                return access_token
            else:
                print(f"❌ Error: No accessToken in response: {data}")
                return None
        else:
            print(f"❌ Error exchanging tokenId: Status {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting Dhan access_token: {e}")
        import traceback
        traceback.print_exc()
        return None

def initialize_dhan():
    """
    Initialize Dhan authentication following the 3-step OAuth flow.
    Reference: https://dhanhq.co/docs/v2/authentication/
    
    STEP 1: Generate Consent → Get consentAppId
    STEP 2: Browser Login → User logs in, redirected with tokenId
    STEP 3: Consume Consent → Exchange tokenId for access_token
    """
    global dhan_access_token, dhan, dhan_client_id
    
    # Validate credentials are set
    if dhan_client_id == "YOUR_DHAN_CLIENT_ID" or dhan_api_key == "YOUR_DHAN_API_KEY" or dhan_api_secret == "YOUR_DHAN_API_SECRET":
        print("\n❌ Dhan credentials not configured!")
        print("Please set the following in Test.py:")
        print("  - dhan_client_id (your Dhan Client ID from profile)")
        print("  - dhan_api_key (from DhanHQ APIs section)")
        print("  - dhan_api_secret (from DhanHQ APIs section)")
        return False
    
    # Check if we already have access_token
    if dhan_access_token and dhan:
        print("✅ Dhan already authenticated and initialized")
        return True
    
    print("\n" + "="*60)
    print("🔐 DHAN AUTHENTICATION (3-Step OAuth Flow)")
    print("="*60)
    print("Following Dhan OAuth flow as per:")
    print("https://dhanhq.co/docs/v2/authentication/")
    print("="*60 + "\n")
    
    # STEP 1: Generate Consent
    consent_app_id = generate_dhan_consent()
    if not consent_app_id:
        print("\n❌ Failed to generate Dhan consent")
        return False
    
    # STEP 2: Open browser for login
    open_dhan_browser_login(consent_app_id)
    
    # STEP 3: Poll for tokenId from callback service
    print(f"\nWaiting for Dhan login to complete...")
    print(f"After login, Dhan will redirect to: {dhan_redirect_uri}")
    print("Polling for tokenId...")
    
    token_id = poll_dhan_token_id()
    
    if not token_id:
        print("\n❌ Dhan tokenId not found.")
        print("Please complete Dhan login in browser.")
        print(f"Expected callback URL: {dhan_redirect_uri}")
        return False
    
    # STEP 3: Exchange tokenId for access_token
    access_token = get_dhan_access_token(token_id)
    
    if not access_token:
        print("\n❌ Failed to get Dhan access_token")
        return False
    
    dhan_access_token = access_token
    
    # Initialize Dhan - dhanhq takes client_id and access_token directly
    try:
        # Based on dhanhq library: dhanhq(client_id, access_token)
        dhan = dhanhq(dhan_client_id, dhan_access_token)
        print("\n✅ Dhan initialized successfully!")
        print("="*60 + "\n")
        return True
    except Exception as e:
        print(f"\n❌ Error initializing Dhan: {e}")
        import traceback
        traceback.print_exc()
        return False

# Global Dhan object (will be initialized when needed)
dhan = None

# =========================
# INITIALIZE DHAN AUTHENTICATION
# Initialize Dhan in parallel with Fyers so it's ready when needed
# =========================
print("\n" + "="*60)
print("🔐 INITIALIZING DHAN AUTHENTICATION")
print("="*60)
print("Initializing Dhan authentication now so it's ready when needed...")
print("="*60 + "\n")

# Initialize Dhan authentication (will open browser for login if needed)
dhan_initialized = initialize_dhan()

if not dhan_initialized:
    print("\n⚠️  WARNING: Dhan authentication failed or incomplete.")
    print("Dhan trades will not execute until authentication is complete.")
    print("You can complete Dhan login later, or restart the script.")
else:
    print("✅ Dhan is ready and authenticated!")

print("\n" + "="*60)
print("✅ BOTH FYERS AND DHAN ARE READY")
print("="*60)
print("Monitoring Fyers orderbook for trade triggers...")
print("="*60 + "\n")

## After this point you can call the relevant apis and get started with

####################################################################################################################
"""
1. User Apis : This includes (Profile,Funds,Holdings)
"""

# =========================
# Global state for trade monitoring
# =========================
fyers_order_count = 0
dhan_trades_active = False
dhan_trade_ids = []  # Store Dhan trade IDs for exit

# =========================
# Dhan API functions
# =========================
def execute_dhan_trades():
    """
    Execute set of trades on Dhan platform.
    TODO: Update with actual trade details once provided.
    """
    global dhan_trades_active, dhan_trade_ids, dhan
    
    print("\n" + "="*60)
    print("🚀 EXECUTING TRADES ON DHAN")
    print("="*60)
    
    # Check if Dhan is initialized (should already be done at startup)
    if not dhan:
        print("⚠️  Dhan not initialized. Attempting to initialize now...")
        if not initialize_dhan():
            print("❌ Failed to initialize Dhan. Cannot execute trades.")
            return
    
    try:
        dhan_trade_ids = []
        
        # TODO: Replace with actual trade details you provide
        # Example trades (update with your actual trades):
        trades_to_execute = [
            # {
            #     'security_id': '1333',  # Example: HDFC Bank
            #     'exchange_segment': dhan.NSE,
            #     'transaction_type': dhan.BUY,
            #     'quantity': 10,
            #     'order_type': dhan.MARKET,
            #     'product_type': dhan.INTRA,
            #     'price': 0
            # },
            # Add more trades as needed
        ]
        
        if not trades_to_execute:
            print("⚠️  No trades configured yet. Waiting for trade details...")
            print("Please provide the trade details to execute.")
            return
        
        print(f"Executing {len(trades_to_execute)} trade(s) on Dhan...")
        
        for i, trade in enumerate(trades_to_execute, 1):
            try:
                print(f"\n📊 Placing trade {i}/{len(trades_to_execute)}...")
                print(f"   Security ID: {trade['security_id']}")
                print(f"   Exchange: {trade['exchange_segment']}")
                print(f"   Type: {trade['transaction_type']}")
                print(f"   Quantity: {trade['quantity']}")
                
                # Place order
                order_response = dhan.place_order(
                    security_id=trade['security_id'],
                    exchange_segment=trade['exchange_segment'],
                    transaction_type=trade['transaction_type'],
                    quantity=trade['quantity'],
                    order_type=trade['order_type'],
                    product_type=trade['product_type'],
                    price=trade.get('price', 0)
                )
                
                if order_response:
                    order_id = order_response.get('orderId') or order_response.get('order_id')
                    if order_id:
                        dhan_trade_ids.append(order_id)
                        print(f"   ✅ Order placed! Order ID: {order_id}")
                    else:
                        print(f"   ⚠️  Order response: {order_response}")
                else:
                    print(f"   ❌ Failed to place order")
                    
            except Exception as e:
                print(f"   ❌ Error placing trade {i}: {e}")
        
        if dhan_trade_ids:
            dhan_trades_active = True
            print(f"\n✅ Successfully placed {len(dhan_trade_ids)} order(s) on Dhan")
            print(f"   Order IDs: {dhan_trade_ids}")
        else:
            print("\n⚠️  No orders were successfully placed")
        
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error executing Dhan trades: {e}")
        import traceback
        traceback.print_exc()

def exit_dhan_trades():
    """
    Exit all active trades on Dhan platform.
    This will cancel all orders placed via execute_dhan_trades()
    """
    global dhan_trades_active, dhan_trade_ids, dhan
    
    print("\n" + "="*60)
    print("🛑 EXITING TRADES ON DHAN")
    print("="*60)
    
    if not dhan:
        print("⚠️  Dhan not initialized. Nothing to exit.")
        return
    
    if not dhan_trade_ids:
        print("⚠️  No active Dhan trades to exit.")
        dhan_trades_active = False
        return
    
    try:
        print(f"Cancelling {len(dhan_trade_ids)} order(s)...")
        
        cancelled_count = 0
        for order_id in dhan_trade_ids:
            try:
                print(f"   Cancelling order ID: {order_id}...")
                cancel_response = dhan.cancel_order(order_id)
                
                if cancel_response:
                    print(f"   ✅ Order {order_id} cancelled")
                    cancelled_count += 1
                else:
                    print(f"   ⚠️  Cancel response: {cancel_response}")
                    
            except Exception as e:
                print(f"   ❌ Error cancelling order {order_id}: {e}")
        
        print(f"\n✅ Cancelled {cancelled_count}/{len(dhan_trade_ids)} order(s)")
        print("="*60 + "\n")
        
        # Clear trade IDs and mark as inactive
        dhan_trade_ids = []
        dhan_trades_active = False
        
    except Exception as e:
        print(f"\n❌ Error exiting Dhan trades: {e}")
        import traceback
        traceback.print_exc()

def is_order_successful(order):
    """
    Check if an order is successful/executed.
    Based on Fyers API, status codes:
    - Status 1: Unknown
    - Status 2: Pending
    - Status 3: Partially Filled
    - Status 4: Filled/Executed (SUCCESS)
    - Status 5: Cancelled
    - Status 6: Rejected
    
    We consider status 4 (Filled) as successful.
    Also accept partially filled (status 3) as it indicates execution started.
    """
    status = order.get('status')
    # Status 4 = Filled/Executed, Status 3 = Partially Filled
    return status in [3, 4]

def poll_fyers_orderbook():
    """
    Poll Fyers orderbook every second to monitor for NEW orders (ignores existing orders at startup).
    - When first NEW successful order appears: Execute Dhan trades
    - When second NEW order appears: Exit Dhan trades
    """
    global fyers_order_count, dhan_trades_active
    
    print("\n" + "="*60)
    print("📊 MONITORING FYERS ORDERBOOK")
    print("="*60)
    print("Getting initial orderbook state (existing orders will be ignored)...")
    
    # Get initial orderbook to identify existing orders
    initial_order_ids = set()
    try:
        initial_response = fyers.orderbook()
        if initial_response and initial_response.get('s') == 'ok':
            initial_orderbook = initial_response.get('orderBook', [])
            initial_order_ids = {order.get('id') for order in initial_orderbook if order.get('id')}
            if initial_order_ids:
                print(f"⚠️  Found {len(initial_order_ids)} existing order(s) - these will be IGNORED")
                print(f"   Existing order IDs: {initial_order_ids}")
            else:
                print("✅ No existing orders found - monitoring for new orders only")
        else:
            print("⚠️  Could not fetch initial orderbook, proceeding anyway...")
    except Exception as e:
        print(f"⚠️  Error fetching initial orderbook: {e}")
        print("Proceeding with monitoring (may include existing orders)...")
    
    print("\nPolling every second for NEW orders...")
    print("Waiting for first NEW successful order to trigger Dhan trades...")
    print("="*60 + "\n")
    
    previous_order_ids = initial_order_ids.copy()  # Start with existing orders
    new_orders_detected = []  # Track new orders that appeared after startup
    first_new_successful_order_detected = False
    
    while True:
        try:
            orderbook_response = fyers.orderbook()
            
            if orderbook_response and orderbook_response.get('s') == 'ok':
                orderbook = orderbook_response.get('orderBook', [])
                current_order_ids = {order.get('id') for order in orderbook if order.get('id')}
                
                # Check for NEW orders (not in initial set and not seen before)
                new_order_ids = current_order_ids - previous_order_ids
                
                if new_order_ids:
                    print(f"🆕 NEW order(s) detected (after startup): {new_order_ids}")
                    # Track these new orders
                    for order_id in new_order_ids:
                        if order_id not in new_orders_detected:
                            new_orders_detected.append(order_id)
                    
                    # Check if any of the new orders are successful
                    new_successful_orders = [
                        order for order in orderbook 
                        if order.get('id') in new_order_ids and is_order_successful(order)
                    ]
                    
                    # Detect first NEW successful order
                    if new_successful_orders and not first_new_successful_order_detected:
                        first_new_successful_order_detected = True
                        print(f"\n✅ FIRST NEW SUCCESSFUL ORDER DETECTED! (After startup)")
                        for order in new_successful_orders:
                            print(f"   Order ID: {order.get('id')}, Symbol: {order.get('symbol')}, Status: {order.get('status')}")
                        print("Triggering Dhan trade execution...")
                        execute_dhan_trades()
                        dhan_trades_active = True
                    
                    # Detect second NEW order (any new order, not necessarily successful)
                    # This means a second NEW order was placed on Fyers after startup
                    if len(new_orders_detected) >= 2 and dhan_trades_active:
                        print(f"\n⚠️  SECOND NEW ORDER DETECTED! (Total new orders: {len(new_orders_detected)})")
                        print(f"   New order IDs: {new_orders_detected}")
                        for order_id in new_orders_detected:
                            order = next((o for o in orderbook if o.get('id') == order_id), None)
                            if order:
                                print(f"   Order: ID={order.get('id')}, Symbol={order.get('symbol')}, Status={order.get('status')}")
                        print("Exiting Dhan trades...")
                        exit_dhan_trades()
                        dhan_trades_active = False
                        print("\n✅ Monitoring stopped. Dhan trades exited.")
                        break
                
                # Update previous order IDs
                previous_order_ids = current_order_ids
                
                # Status update every 10 seconds
                if int(time.time()) % 10 == 0:
                    total_orders = len(orderbook)
                    new_orders_count = len(new_orders_detected)
                    print(f"  📊 Status: {total_orders} total orders ({len(initial_order_ids)} existing, {new_orders_count} new) | Dhan trades: {'Active' if dhan_trades_active else 'Inactive'}")
            
            elif orderbook_response:
                # API returned but with error
                if orderbook_response.get('s') != 'ok':
                    print(f"⚠️  Orderbook API error: {orderbook_response.get('message', 'Unknown error')}")
            
        except Exception as e:
            print(f"❌ Error polling orderbook: {e}")
        
        time.sleep(1)  # Poll every second

# Start monitoring
print("\n🚀 Starting Fyers orderbook monitoring...")
poll_fyers_orderbook()
