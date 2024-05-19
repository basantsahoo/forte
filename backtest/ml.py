import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
#from research.analysis import strategy_analysis
from backtest_2024.analysis import weekly_path_analysis

#strategy_analysis_revised.run()
#combined_analysis.run()
#option_strategy_analysis.run()
#ema_5_strategy_analysis.run()
#visualize_pattern_ema.run()
weekly_path_analysis.run()





"""
Variable definition
dist_frm_level - Distance from nearest hundred
support/resistance : determined by second pass inflex from previous day + cummulative non traded Support/resistance 
from earlier days  

"""