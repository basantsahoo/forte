from causalinference import CausalModel
from causalinference.utils import random_data
#Y is the outcome, D is treatment status, and X is the independent variable
Y, D, X = random_data()
causal = CausalModel(Y, D, X)
print(causal.summary_stats)

from dowhy import CausalModel
import dowhy.datasets
# Load some sample data
data = dowhy.datasets.linear_dataset(
    beta=10,
    num_common_causes=5,
    num_instruments=2,
    num_samples=10000,
    treatment_is_binary=True)
model = CausalModel(
    data=data["df"],
    treatment=data["treatment_name"],
    outcome=data["outcome_name"],
    graph=data["gml_graph"])
model.view_model()
