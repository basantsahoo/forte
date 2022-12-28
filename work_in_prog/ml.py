import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
#from research.analysis import strategy_analysis
#from research.analysis import strategy_analysis_revised
import set_path
from research.analysis import combined_analysis
from research.analysis import visualize_pattern
#strategy_analysis_revised.run()
combined_analysis.run()
