from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv
import uvicorn
from typing import Dict, Any
import logging
import traceback
import json

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
            for position in positions.get("net", []):
                if position["net_quantity"] != 0:  # Only show non-zero positions
                    current_positions.append({
                        "tradingsymbol": position["tradingsymbol"],
                        "net_quantity": position["net_quantity"],
                        "average_price": position["average_price"],
                        "pnl": position["pnl"]
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)