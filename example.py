# Setup the FOPPL-compiler and auto-importer:
from foppl import Options, imports
# Print additional information:
Options.debug = True

# Import and compile the model:
import lin_regr as foppl_model

# Print out the entire model:
print(foppl_model.model)

# A sample run with the model:
print("=" * 30)
state = foppl_model.model.gen_prior_samples()
pdf = foppl_model.model.gen_pdf(state)
print("Result: {}\nPDF: {}".format(state.get('result', '?'), pdf))

foppl_model.model.display_graph()
