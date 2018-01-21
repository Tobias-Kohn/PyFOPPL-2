# Setup the FOPPL-compiler and auto-importer:
from foppl import Options, imports
# Print additional information:
Options.debug = True

# Import and compile the model:
import hmm_model_map as foppl_model

# Print out the entire model:
print(foppl_model.model)
foppl_model.model.display_graph()
