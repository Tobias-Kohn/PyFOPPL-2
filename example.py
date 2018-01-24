# Setup the FOPPL-compiler and auto-importer:
from foppl import Options, imports
# Print additional information:
Options.debug = True

# Import and compile the model:
import gmm_model_a as foppl_model

# Print out the entire model:
print(foppl_model.model)

print("=" * 30)
print("CODE")
print(foppl_model.model.gen_prior_samples_code())
print("-" * 30)
print(foppl_model.model.gen_pdf_code())
print("-" * 30)

# A sample run with the model:
print("=" * 30)
state = foppl_model.model.gen_prior_samples()
print("-" * 30)
pdf = foppl_model.model.gen_pdf(state)
print("Result: {}\nPDF: {}".format(foppl_model.model.get_result(state), pdf))

print("=" * 30)

for key in sorted(state.keys()):
    print("{}  -> {}".format(key, state[key]))

foppl_model.model.display_graph()