import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
"""
#from research.analysis import strategy_analysis
from research.analysis import strategy_analysis_revised
from research.analysis import candle_strategy_analysis
from research.analysis import option_strategy_analysis
from research.analysis import ema_5_strategy_analysis
from research.analysis import combined_analysis
from research.analysis import visualize_pattern
from research.analysis import weekly_path_analysis
from research.analysis import visualize_pattern_ema
from research.analysis import buy_put_analysis
from research.analysis import option_market_imapct_spot_analysis
from research.analysis import option_market_imapct_spot_at_low_analysis
"""
from research.analysis import option_market_imapct_sell_analysis
#strategy_analysis_revised.run()
#combined_analysis.run()
#option_strategy_analysis.run()
#ema_5_strategy_analysis.run()
#visualize_pattern_ema.run()
#weekly_path_analysis.run()
option_market_imapct_sell_analysis.scenarios()

