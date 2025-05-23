from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv
import uvicorn
from typing import Dict, Any, List
import logging
import traceback
import json
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Kite MCP Web App")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize KiteConnect
api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")

logger.debug(f"API Key present: {bool(api_key)}")
logger.debug(f"API Secret present: {bool(api_secret)}")

if not api_key or not api_secret:
    raise ValueError("KITE_API_KEY and KITE_API_SECRET must be set in .env file")

kite = KiteConnect(api_key=api_key)

# Store access token in memory (for demo purposes - in production, use proper session management)
access_token: Dict[str, Any] = {}

# Store active WebSocket connections
active_connections: List[WebSocket] = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with login button"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.get("/login")
async def login():
    """Initiate Zerodha login"""
    try:
        login_url = kite.login_url()
        logger.info(f"Generated login URL: {login_url}")
        return RedirectResponse(login_url)
    except Exception as e:
        logger.error(f"Error generating login URL: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating login URL: {str(e)}")

@app.get("/login/redirect")
async def login_redirect(request_token: str):
    """Handle login redirect and generate session"""
    try:
        logger.info(f"Received request token: {request_token}")
        if not request_token:
            raise ValueError("Request token is empty")
            
        data = kite.generate_session(
            request_token,
            api_secret=api_secret
        )
        
        if not data or "access_token" not in data:
            raise ValueError("Invalid response from Zerodha API")
            
        # Store the access token
        access_token["token"] = data["access_token"]
        logger.info("Successfully generated session")
        return RedirectResponse("/dashboard")
    except Exception as e:
        logger.error(f"Error generating session: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error generating session: {str(e)}")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard showing user's portfolio"""
    try:
        if not access_token.get("token"):
            logger.warning("No access token found, redirecting to login")
            return RedirectResponse("/login")

        # Set the access token
        kite.set_access_token(access_token["token"])
        logger.info("Access token set successfully")

        try:
            # Get user's holdings
            logger.debug("Fetching holdings...")
            holdings = kite.holdings()
            logger.info(f"Retrieved {len(holdings)} holdings")
            
            # Get user's positions
            logger.debug("Fetching positions...")
            positions = kite.positions()
            logger.info(f"Retrieved positions data")
            logger.debug(f"Positions data structure: {json.dumps(positions, indent=2)}")
            
            # Get user's margins
            logger.debug("Fetching margins...")
            margins = kite.margins()
            logger.info("Retrieved margins data")
            logger.debug(f"Margins data structure: {json.dumps(margins, indent=2)}")

            # Process holdings data
            portfolio = []
            for holding in holdings:
                if holding["quantity"] > 0:  # Only show non-zero holdings
                    portfolio.append({
                        "tradingsymbol": holding["tradingsymbol"],
                        "quantity": holding["quantity"],
                        "average_price": holding["average_price"],
                        "last_price": holding["last_price"],
                        "pnl": holding["pnl"]
                    })

            # Process positions data
            current_positions = []
            if positions and "net" in positions:
                for position in positions["net"]:
                    # Check if the position has a non-zero quantity
                    if position.get("quantity", 0) != 0:
                        current_positions.append({
                            "tradingsymbol": position["tradingsymbol"],
                            "net_quantity": position["quantity"],
                            "average_price": position["average_price"],
                            "pnl": position.get("pnl", 0)
                        })
            
            return templates.TemplateResponse(
                "dashboard.html",
                {
                    "request": request,
                    "portfolio": portfolio,
                    "positions": current_positions,
                    "margins": margins
                }
            )
        except Exception as e:
            error_msg = f"Error fetching data: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except Exception as e:
        error_msg = f"Dashboard error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

@app.get("/refresh")
async def refresh_data():
    """Refresh dashboard data"""
    try:
        if not access_token.get("token"):
            logger.warning("No access token found in refresh_data")
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated. Please login again."}
            )

        # Set the access token
        kite.set_access_token(access_token["token"])
        logger.info("Access token set successfully in refresh_data")

        try:
            # Get fresh data
            logger.debug("Fetching holdings...")
            holdings = kite.holdings()
            logger.info(f"Retrieved {len(holdings)} holdings")
            
            logger.debug("Fetching positions...")
            positions = kite.positions()
            logger.info("Retrieved positions data")
            
            logger.debug("Fetching margins...")
            margins = kite.margins()
            logger.info("Retrieved margins data")
            logger.debug(f"Margins data structure: {json.dumps(margins, indent=2)}")

            # Process holdings data
            portfolio = []
            for holding in holdings:
                if holding["quantity"] > 0:
                    portfolio.append({
                        "tradingsymbol": holding["tradingsymbol"],
                        "quantity": holding["quantity"],
                        "average_price": holding["average_price"],
                        "last_price": holding["last_price"],
                        "pnl": holding["pnl"]
                    })

            # Process positions data
            current_positions = []
            if positions and "net" in positions:
                for position in positions["net"]:
                    if position.get("quantity", 0) != 0:
                        current_positions.append({
                            "tradingsymbol": position["tradingsymbol"],
                            "net_quantity": position["quantity"],
                            "average_price": position["average_price"],
                            "pnl": position.get("pnl", 0)
                        })

            return {
                "portfolio": portfolio,
                "positions": current_positions,
                "margins": margins
            }
        except Exception as e:
            error_msg = f"Error fetching data: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return JSONResponse(
                status_code=400,
                content={"error": f"Error fetching data: {str(e)}"}
            )
    except Exception as e:
        error_msg = f"Refresh data error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"}
        )

@app.post("/api/place_order")
async def place_order(order_data: dict):
    """Place a new order"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Not authenticated. Please login again."}
            )

        kite.set_access_token(access_token["token"])

        # Prepare order parameters
        order_params = {
            "tradingsymbol": order_data["symbol"],
            "quantity": int(order_data["quantity"]),
            "transaction_type": order_data["transactionType"],
            "order_type": order_data["orderType"],
            "product": "CNC",  # Cash and Carry
            "exchange": "NSE"
        }

        # Add price for limit orders
        if order_data["orderType"] == "LIMIT" and order_data.get("price"):
            order_params["price"] = float(order_data["price"])

        # Place the order
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            **order_params
        )

        return {"success": True, "order_id": order_id}
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}

@app.get("/api/orders")
async def get_orders():
    """Get order book"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated. Please login again."}
            )

        kite.set_access_token(access_token["token"])

        # Get orders
        orders = kite.orders()
        
        # Process orders for display
        processed_orders = []
        for order in orders:
            processed_orders.append({
                "order_id": order["order_id"],
                "symbol": order["tradingsymbol"],
                "type": f"{order['transaction_type']} {order['order_type']}",
                "status": order["status"],
                "quantity": order["quantity"],
                "price": order.get("price", "Market")
            })

        return processed_orders
    except Exception as e:
        logger.error(f"Error fetching orders: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/cancel_order/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an existing order"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Not authenticated. Please login again."}
            )

        kite.set_access_token(access_token["token"])

        # Cancel the order
        kite.cancel_order(
            variety=kite.VARIETY_REGULAR,
            order_id=order_id
        )

        return {"success": True}
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}

@app.get("/api/portfolio")
async def get_portfolio():
    """Get current portfolio"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated. Please login again."}
            )

        kite.set_access_token(access_token["token"])

        # Get holdings
        holdings = kite.holdings()
        
        # Process holdings for display
        portfolio = []
        for holding in holdings:
            if holding["quantity"] > 0:
                portfolio.append({
                    "symbol": holding["tradingsymbol"],
                    "quantity": holding["quantity"],
                    "average_price": holding["average_price"],
                    "last_price": holding["last_price"],
                    "pnl": holding["pnl"]
                })

        return portfolio
    except Exception as e:
        logger.error(f"Error fetching portfolio: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                # Parse the incoming message
                message = json.loads(data)
                
                # Handle different types of requests
                if message.get("type") == "auth":
                    # Handle authentication
                    access_token_value = message.get("access_token")
                    if access_token_value:
                        kite.set_access_token(access_token_value)
                        await websocket.send_json({
                            "type": "auth_response",
                            "status": "success"
                        })
                
                elif message.get("type") == "subscribe":
                    # Handle subscription requests
                    symbols = message.get("symbols", [])
                    if symbols:
                        try:
                            # Subscribe to real-time data
                            kite.subscribe(symbols)
                            await websocket.send_json({
                                "type": "subscription_response",
                                "status": "success",
                                "symbols": symbols
                            })
                        except Exception as e:
                            logger.error(f"Error subscribing to symbols: {str(e)}")
                            await websocket.send_json({
                                "type": "subscription_response",
                                "status": "error",
                                "message": str(e)
                            })
                
                elif message.get("type") == "request":
                    # Handle data requests
                    endpoint = message.get("endpoint")
                    params = message.get("params", {})
                    
                    try:
                        # Map endpoints to KiteConnect methods
                        if endpoint == "portfolio":
                            data = kite.portfolio()
                        elif endpoint == "positions":
                            data = kite.positions()
                        elif endpoint == "orders":
                            data = kite.orders()
                        elif endpoint == "holdings":
                            data = kite.holdings()
                        elif endpoint == "margins":
                            data = kite.margins()
                        elif endpoint == "quote":
                            data = kite.quote(params.get("symbols", []))
                        elif endpoint == "ltp":
                            data = kite.ltp(params.get("symbols", []))
                        else:
                            data = {"error": "Invalid endpoint"}
                        
                        await websocket.send_json({
                            "type": "response",
                            "endpoint": endpoint,
                            "data": data
                        })
                    except Exception as e:
                        logger.error(f"Error processing request: {str(e)}")
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
    finally:
        active_connections.remove(websocket)

# Add MCP-specific error handling
class MCPError(Exception):
    """Base class for MCP-specific errors"""
    pass

class MCPAuthenticationError(MCPError):
    """Raised when there's an authentication error"""
    pass

class MCPSubscriptionError(MCPError):
    """Raised when there's an error subscribing to symbols"""
    pass

# Add MCP-specific error handlers
@app.exception_handler(MCPError)
async def mcp_exception_handler(request: Request, exc: MCPError):
    """Handle MCP-specific exceptions"""
    return JSONResponse(
        status_code=400,
        content={
            "error": str(exc),
            "type": exc.__class__.__name__
        }
    )

# Add MCP-specific authentication middleware
@app.middleware("http")
async def mcp_auth_middleware(request: Request, call_next):
    """Middleware to handle MCP authentication"""
    try:
        if request.url.path.startswith("/api/"):
            if not access_token.get("token"):
                raise MCPAuthenticationError("Not authenticated")
            kite.set_access_token(access_token["token"])
        response = await call_next(request)
        return response
    except MCPAuthenticationError as e:
        return JSONResponse(
            status_code=401,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Middleware error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@app.get("/api/auth_status")
async def check_auth_status():
    """Check if user is authenticated"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=200,
                content={"authenticated": False}
            )
        return JSONResponse(
            status_code=200,
            content={"authenticated": True}
        )
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/quotes")
async def get_quotes(symbols: dict):
    """Get quotes for multiple symbols"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        quotes = kite.quote(symbols["symbols"])
        
        formatted_quotes = []
        for symbol, quote in quotes.items():
            formatted_quotes.append({
                "symbol": symbol,
                "last_price": quote["last_price"],
                "change_percent": quote["change_percent"]
            })
        
        return JSONResponse(content=formatted_quotes)
    except Exception as e:
        logger.error(f"Error fetching quotes: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/historical/{symbol}")
async def get_historical_data(symbol: str, days: int = 30):
    """Get historical data for a symbol"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        
        # Get historical data
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        data = kite.historical_data(
            instrument_token=kite.ltp(symbol)[symbol]["instrument_token"],
            from_date=start_date,
            to_date=end_date,
            interval="day"
        )
        
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/mf_holdings")
async def get_mf_holdings():
    """Get mutual fund holdings"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        holdings = kite.mf_holdings()
        
        return JSONResponse(content=holdings)
    except Exception as e:
        logger.error(f"Error fetching MF holdings: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/mf_orders")
async def get_mf_orders():
    """Get mutual fund orders"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        orders = kite.mf_orders()
        
        return JSONResponse(content=orders)
    except Exception as e:
        logger.error(f"Error fetching MF orders: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/place_mf_order")
async def place_mf_order(order_data: dict):
    """Place a mutual fund order"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        
        order = kite.place_mf_order(
            tradingsymbol=order_data["symbol"],
            amount=order_data["amount"],
            transaction_type="BUY"
        )
        
        return JSONResponse(content={"success": True, "order_id": order})
    except Exception as e:
        logger.error(f"Error placing MF order: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/cancel_mf_order/{order_id}")
async def cancel_mf_order(order_id: str):
    """Cancel a mutual fund order"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        kite.cancel_mf_order(order_id)
        
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error cancelling MF order: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/mf_sips")
async def get_mf_sips():
    """Get mutual fund SIPs"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        sips = kite.mf_sips()
        
        return JSONResponse(content=sips)
    except Exception as e:
        logger.error(f"Error fetching MF SIPs: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/create_sip")
async def create_sip(sip_data: dict):
    """Create a new SIP"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        
        sip = kite.place_mf_sip(
            tradingsymbol=sip_data["symbol"],
            amount=sip_data["amount"],
            frequency="monthly",
            installments=sip_data["installments"]
        )
        
        return JSONResponse(content={"success": True, "sip_id": sip})
    except Exception as e:
        logger.error(f"Error creating SIP: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/modify_sip/{sip_id}")
async def modify_sip(sip_id: str, sip_data: dict):
    """Modify an existing SIP"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        kite.modify_mf_sip(sip_id, amount=sip_data["amount"])
        
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error modifying SIP: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/cancel_sip/{sip_id}")
async def cancel_sip(sip_id: str):
    """Cancel a SIP"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        kite.cancel_mf_sip(sip_id)
        
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error cancelling SIP: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/available_mf")
async def get_available_mf():
    """Get list of available mutual funds"""
    try:
        if not access_token.get("token"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"}
            )

        kite.set_access_token(access_token["token"])
        funds = kite.mf_instruments()
        
        return JSONResponse(content=funds)
    except Exception as e:
        logger.error(f"Error fetching available MF: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/logout")
async def logout():
    """Handle user logout"""
    try:
        # Clear the access token
        access_token.clear()
        logger.info("User logged out successfully")
        
        # Redirect to home page
        return RedirectResponse("/")
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        logger.error(traceback.format_exc())
        return RedirectResponse("/")

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request):
    """Advanced analytics dashboard"""
    if not access_token.get("token"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("analytics.html", {"request": request})

@app.get("/api/portfolio/analytics")
async def get_portfolio_analytics():
    """Get portfolio analytics data"""
    try:
        if not access_token.get("token"):
            raise HTTPException(status_code=401, detail="Not authenticated")

        kite.set_access_token(access_token["token"])
        
        # Get holdings and positions
        holdings = kite.holdings()
        positions = kite.positions()
        
        # Calculate metrics
        metrics = calculate_portfolio_metrics(holdings, positions)
        
        # Calculate sector allocation
        sector_allocation = calculate_sector_allocation(holdings)
        
        # Calculate asset class distribution
        asset_distribution = calculate_asset_distribution(holdings)
        
        # Calculate performance data
        performance = calculate_performance_data(holdings)
        
        # Calculate risk metrics
        risk_metrics = calculate_risk_metrics(holdings)
        
        return {
            "metrics": metrics,
            "sectorAllocation": sector_allocation,
            "assetClassDistribution": asset_distribution,
            "performance": performance,
            "riskMetrics": risk_metrics
        }
    except Exception as e:
        logger.error(f"Error in portfolio analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_portfolio_metrics(holdings, positions):
    """Calculate key portfolio metrics"""
    total_value = sum(holding["last_price"] * holding["quantity"] for holding in holdings)
    daily_pnl = sum(holding["pnl"] for holding in holdings)
    
    # Calculate returns for Sharpe ratio
    returns = [holding["pnl"] / (holding["average_price"] * holding["quantity"]) 
              for holding in holdings if holding["quantity"] > 0]
    
    if returns:
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) != 0 else 0
    else:
        sharpe_ratio = 0
    
    # Calculate beta (simplified)
    beta = 1.0  # Placeholder - would need historical data for proper calculation
    
    return {
        "totalValue": total_value,
        "dailyPnL": daily_pnl,
        "sharpeRatio": sharpe_ratio,
        "beta": beta
    }

def calculate_sector_allocation(holdings):
    """Calculate sector allocation of portfolio"""
    sector_values = defaultdict(float)
    
    for holding in holdings:
        if holding["quantity"] > 0:
            # Get sector information (you would need to maintain a mapping of stocks to sectors)
            sector = get_stock_sector(holding["tradingsymbol"])
            value = holding["last_price"] * holding["quantity"]
            sector_values[sector] += value
    
    total_value = sum(sector_values.values())
    
    # Convert to percentages
    labels = []
    values = []
    for sector, value in sector_values.items():
        labels.append(sector)
        values.append((value / total_value) * 100)
    
    return {
        "labels": labels,
        "values": values
    }

def calculate_asset_distribution(holdings):
    """Calculate asset class distribution"""
    asset_values = defaultdict(float)
    
    for holding in holdings:
        if holding["quantity"] > 0:
            # Determine asset class (equity, debt, etc.)
            asset_class = get_asset_class(holding["tradingsymbol"])
            value = holding["last_price"] * holding["quantity"]
            asset_values[asset_class] += value
    
    total_value = sum(asset_values.values())
    
    # Convert to percentages
    labels = []
    values = []
    for asset_class, value in asset_values.items():
        labels.append(asset_class)
        values.append((value / total_value) * 100)
    
    return {
        "labels": labels,
        "values": values
    }

def calculate_performance_data(holdings):
    """Calculate performance data for chart"""
    # This is a simplified version - in reality, you'd want historical data
    dates = [(datetime.now() - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(30, 0, -1)]
    
    # Placeholder data - in reality, you'd calculate this from historical prices
    portfolio_values = [100000 * (1 + 0.001 * i) for i in range(30)]
    benchmark_values = [100000 * (1 + 0.0008 * i) for i in range(30)]
    
    return {
        "dates": dates,
        "portfolioValues": portfolio_values,
        "benchmarkValues": benchmark_values
    }

def calculate_risk_metrics(holdings):
    """Calculate risk metrics for the portfolio"""
    # These are simplified calculations - in reality, you'd need historical data
    return {
        "volatility": 0.15,  # 15% annualized volatility
        "beta": 1.0,
        "sharpeRatio": 1.5,
        "alpha": 0.02,  # 2% alpha
        "informationRatio": 0.8
    }

def get_stock_sector(tradingsymbol):
    """Get sector for a stock (placeholder - you would need to maintain this mapping)"""
    # This is a placeholder - you would need to maintain a mapping of stocks to sectors
    sectors = {
        "RELIANCE": "Energy",
        "TCS": "IT",
        "HDFCBANK": "Banking",
        "INFY": "IT",
        # Add more mappings as needed
    }
    return sectors.get(tradingsymbol, "Others")

def get_asset_class(tradingsymbol):
    """Get asset class for a security (placeholder - you would need to maintain this mapping)"""
    # This is a placeholder - you would need to maintain a mapping of securities to asset classes
    asset_classes = {
        "RELIANCE": "Equity",
        "TCS": "Equity",
        "HDFCBANK": "Equity",
        "INFY": "Equity",
        # Add more mappings as needed
    }
    return asset_classes.get(tradingsymbol, "Others")

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """Orders page showing order history and order placement form"""
    try:
        if not access_token.get("token"):
            logger.warning("No access token found, redirecting to login")
            return RedirectResponse("/login")

        # Set the access token
        kite.set_access_token(access_token["token"])
        logger.info("Access token set successfully")

        return templates.TemplateResponse("orders.html", {"request": request})
    except Exception as e:
        error_msg = f"Orders page error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

@app.get("/positions", response_class=HTMLResponse)
async def positions_page(request: Request):
    """Positions page showing current positions"""
    try:
        if not access_token.get("token"):
            logger.warning("No access token found, redirecting to login")
            return RedirectResponse("/login")

        # Set the access token
        kite.set_access_token(access_token["token"])
        logger.info("Access token set successfully")

        return templates.TemplateResponse("positions.html", {"request": request})
    except Exception as e:
        error_msg = f"Positions page error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)