# Kite MCP

A Model Context Protocol (MCP) server for Zerodha Kite integration, providing a comprehensive web interface for managing your trading portfolio, orders, and analytics.

## Prerequisites

1. Python 3.8 or higher
2. Zerodha Kite Developer Account
   - Sign up at [Zerodha Developer Portal](https://developers.kite.trade/)
   - Create a new application to get your API key and secret
   - Set up your redirect URL (e.g., `http://localhost:8000/login/redirect`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/pranaypatel512/KiteMCP.git
cd KiteMCP
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Create a `.env` file in the project root with your Zerodha credentials:
```env
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
REDIRECT_URL=http://localhost:8000/login/redirect  # Must match the URL configured in your Zerodha Developer Console
```

Note: The `REDIRECT_URL` must exactly match the URL you configured in your Zerodha Developer Console. This is the URL where Zerodha will redirect after successful authentication. Make sure to:
- Use the correct protocol (http/https)
- Include the correct port number
- Match the exact path (/login/redirect)
- Update this URL in both your .env file and Zerodha Developer Console if you change it

## Usage

1. Start the MCP server:
```bash
python main.py
```

2. Open your browser and navigate to `http://localhost:8000`

3. Click the login button to authenticate with Zerodha Kite

## Features

### Dashboard
- Real-time portfolio overview
- Current positions
- Margin information
- Quick order placement
- Portfolio value tracking

### Orders
- View all orders (pending, completed, rejected)
- Place new orders
- Cancel pending orders
- Order history and status tracking

### Positions
- Current open positions
- Position details (entry price, current price, P&L)
- Position modification options

### Analytics
- Portfolio performance metrics
- Sector allocation analysis
- Asset distribution visualization
- Risk metrics calculation
- Historical performance tracking

### Mutual Funds
- View MF holdings
- Place MF orders
- Manage SIPs
- Track MF performance

### AI Chat Assistant
- Get help with Kite's functionality
- Query about trading strategies
- Understand market concepts
- Get real-time assistance

## WebSocket Features
- Real-time portfolio updates
- Live price updates
- Instant order status notifications
- Position updates

## Security
- Secure API key management
- Session-based authentication
- Environment variable protection
- Secure WebSocket connections

## Development
- Built with FastAPI
- Uses WebSocket for real-time updates
- Jinja2 templates for UI
- Modular code structure

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.