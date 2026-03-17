import sys

file_path = "/Users/lightwing/Desktop/antigravity/app/web.py"
with open(file_path, "r") as f:
    text = f.read()

# 1. Add is_dock_prefetch
text = text.replace(
    '    def render_workspace_page(current_view: str, settings_section: str = "about"):\n        requested_tickers = parse_requested_tickers()',
    '    def render_workspace_page(current_view: str, settings_section: str = "about"):\n        is_dock_prefetch = request.headers.get("X-Requested-With") == "dock-prefetch"\n        requested_tickers = parse_requested_tickers()'
)

# 2. Replace trade-messages block
trade_old = """            if current_view == "trade-messages":
                if requested_tickers:
                    trade_ticker = validate_ticker_or_raise(requested_tickers[0])"""

trade_new = """            if current_view == "trade-messages":
                if requested_tickers:
                    if is_dock_prefetch:
                        ticker_slots = [normalize_ticker_input(requested_tickers[0]) or requested_tickers[0]]
                        trade_backtest_result = type("Mock", (), {"summary": type("Mock", (), {"net_return_pct": 0.0, "final_equity": 0.0, "max_drawdown_pct": 0.0, "win_rate_pct": 0.0, "trade_count": 0, "initial_capital": 0.0})(), "trades": [], "chart": {"datasets": [], "labels": []}})()
                        continue_process_trade = False
                    else:
                        trade_ticker = validate_ticker_or_raise(requested_tickers[0])
                        continue_process_trade = True
                    if continue_process_trade:"""

text = text.replace(trade_old, trade_new)

# Since we wrapped trade_ticker inside `if continue_process_trade:`, we need to indent everything until the `elif current_view in {"tickers", ...}

idx_elif = text.find('            elif current_view in {"tickers", "portfolio"}:')
idx_if_trade = text.find('                    if continue_process_trade:')

if idx_elif != -1 and idx_if_trade != -1:
    before = text[:idx_if_trade]
    after = text[idx_elif:]
    # lines to indent
    lines_to_indent = text[idx_if_trade:idx_elif].split('\n')
    indented = []
    for i, line in enumerate(lines_to_indent):
        if i == 0:
            indented.append(line) # keep 'if continue_process_trade:'
        elif line.strip() == "":
            indented.append(line)
        else:
            indented.append("    " + line)
    
    text = before + '\n'.join(indented) + after

# 3. Replace tickers block
tickers_old = """            elif current_view in {"tickers", "portfolio"}:
                if requested_tickers and len(requested_tickers) >= MIN_TICKERS:
                    validated_tickers = [validate_ticker_or_raise(ticker) for ticker in requested_tickers]"""

tickers_new = """            elif current_view in {"tickers", "portfolio"}:
                if requested_tickers and len(requested_tickers) >= MIN_TICKERS:
                    if is_dock_prefetch:
                        validated_tickers = [normalize_ticker_input(t) or t for t in requested_tickers]
                        profiles = [type("Mock", (), {"company_name": t, "logo_url": ""})() for t in validated_tickers]
                        if current_view == "portfolio":
                            portfolio_weights = requested_weights or [0] * len(validated_tickers)
                            portfolio_items = [{"ticker": t, "company_name": t, "logo_url": "", "weight": w, "growth_multiple": 1.0, "color": "transparent"} for t, w in zip(validated_tickers, portfolio_weights)]
                            portfolio_total_return = 0.0
                        else:
                            series = [type("Mock", (), {"ticker": t, "normalized_returns": [0.0], "color": "transparent"})() for t in validated_tickers]
                            performance_items = [{"ticker": t, "company_name": t, "logo_url": "", "ending_return": 0.0, "color": "transparent", "shadow_color": "transparent", "is_winner": False} for t in validated_tickers]
                        common_start = pd.Timestamp.now()
                        common_end = pd.Timestamp.now()
                        display_range = "Loading range..."
                        ticker_slots = validated_tickers.copy()
                        continue_process_tickers = False
                    else:
                        validated_tickers = [validate_ticker_or_raise(ticker) for ticker in requested_tickers]
                        continue_process_tickers = True
                    if continue_process_tickers:"""

text = text.replace(tickers_old, tickers_new)

idx_except = text.find('        except Exception as exc:  # noqa: BLE001')
idx_if_tickers = text.find('                    if continue_process_tickers:')

if idx_except != -1 and idx_if_tickers != -1:
    before = text[:idx_if_tickers]
    after = text[idx_except:]
    lines_to_indent = text[idx_if_tickers:idx_except].split('\n')
    indented = []
    for i, line in enumerate(lines_to_indent):
        if i == 0:
            indented.append(line)
        elif line.strip() == "":
            indented.append(line)
        else:
            indented.append("    " + line)
    
    text = before + '\n'.join(indented) + after

with open(file_path, "w") as f:
    f.write(text)

