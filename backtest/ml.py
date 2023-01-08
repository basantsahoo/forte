import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
#from research.analysis import strategy_analysis
from research.analysis import strategy_analysis_revised
from research.analysis import candle_strategy_analysis
from research.analysis import combined_analysis
from research.analysis import visualize_pattern
#strategy_analysis_revised.run()
#combined_analysis.run()
candle_strategy_analysis.run()





"""
Variable definition
dist_frm_level - Distance from nearest hundred
support/resistance : determined by second pass inflex from previous day + cummulative non traded Support/resistance 
from earlier days  

"""