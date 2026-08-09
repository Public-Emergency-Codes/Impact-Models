# PEC scenarios and calculation inputs

Provenance: workspace transcription reconstructed from the user-supplied PEC
scenario/input material and the modeling requirements retained in the paper
history. This is not the unavailable original binary document.

The source material requires incident-level comparison of the same event under
a baseline pathway and a PEC pathway. The principal model inputs are:

- annual opportunity volume;
- clinical or operational relevance;
- population reach and feature availability;
- noticing, activation, and successful use;
- technical reliability and receiving-system compatibility;
- time, routing, information, or discovery change;
- beneficial and adverse absolute outcome-probability changes;
- overlap among functions acting on the same incident; and
- uncertainty distributions and implementation maturity.

The mortality pathways retained in the executable archive are 988/crisis
connection, 211 referral, 911 diversion/capacity, earlier correct 911 access,
cardiac-arrest bystander assistance, silent/language access,
location/responder access, medical data/photo/video, and contacts/passive
monitoring. Every administrative opportunity count is converted to a latent
unique emergency episode count. A person may contribute multiple episodes per
year. Multiple PEC functions may act within one episode, but the episode
receives one final mortality outcome. The conversion factors cover repeat
records and cross-pathway allocation; they are planning sensitivities rather
than observed national deduplication estimates.

The complete numerical low/mode/high inputs, zero-effect probabilities,
evidence labels, units, and rationales are in
`../config/mortality-model-inputs.json`. Economic pathway distributions and
feature allocations are in `../pec_model/economic_inputs.py`; the public entry
point is `python -m pec_model.economic`.
Those machine-readable files, not this overview, are authoritative for
reproducing the reported calculations.