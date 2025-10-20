#!/usr/bin/env python3
"""
Simple script to run backtesting
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backtest_engine import run_backtest

async def main():
    """Run backtesting"""
    print("🚀 Starting NIFTY50 Options Backtesting...")
    print("=" * 50)
    
    try:
        results = await run_backtest()
        
        if results:
            print(f"\n✅ Backtest completed successfully!")
            print(f"📊 Results saved to: backtest_results.json")
            print(f"🌐 View results in the dashboard at: http://localhost:3000")
        else:
            print("❌ Backtest failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Error running backtest: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)