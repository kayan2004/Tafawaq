"""Prompt for the NeMo Guardrails off-topic classifier."""

CLASSIFICATION_PROMPT = """\
Is the following message about Lebanese Grade 12 Mathematics baccalaureate exam preparation?

In-scope topics ONLY: Functions and their properties, Limits and asymptotes, Derivatives, \
Integrals (including integration by parts and substitution), Complex numbers, \
Geometry in space (vectors/planes/lines), Probability, Numerical sequences, \
Differential equations, Logarithmic and exponential functions.

Message: "{message}"

Answer with only the single word Yes or No."""
