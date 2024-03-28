import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
from research.analysis import option_market_imapct_spot_at_high_analysis_latest
from research.analysis import option_market_imapct_spot_at_low_analysis
from research.analysis import option_market_imapct_spot_at_low_bear_market_analysis
#option_market_imapct_spot_at_low_analysis.scenarios()
option_market_imapct_spot_at_low_bear_market_analysis.scenarios()

