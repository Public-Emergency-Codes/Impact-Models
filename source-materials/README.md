# PEC source-material archive

Release identifier: `pec-prospective-2026-08-09-r9`.

The original binary workspace documents cited during drafting were not present
in the active project directory when the August 8, 2026 reproducibility review
was repaired. The two Markdown files in this directory are therefore labeled
transcriptions, not original binaries. They preserve the PEC function list and
the scenario/input structure available in the paper history.

The canonical executable mortality assumptions are in
`../config/mortality-model-inputs.json`. The canonical executable economic
assumptions are in `../pec_model/economic_inputs.py`; run
`python -m pec_model.economic` to execute the prospective model. The SHA-256
manifest at the project root
allows an archive recipient to verify the exact files used for the reported
results.

The prospective mature mortality release converts administrative records to
latent unique emergency episodes. A person may contribute more than one episode
per year; multiple PEC functions may act within an episode; and the episode is
assigned one final benefit/harm/none mortality outcome. Run
`python scripts/validate_repository.py --rerun --compile` from the project root to
verify JSON uniqueness, the unique-episode metadata, manuscript headline
tokens, manifest hashes, byte-for-byte simulation outputs, and clean LaTeX
compilation.

If the original `.docx` files become available, deposit them beside these
transcriptions and regenerate the manifest; do not silently relabel a
transcription as an original source.

The independent expert-elicitation protocol is deposited in
`../validation/expert-elicitation-protocol.md`. The protocol is specified, but no completed
panel or independent statistical sign-off is claimed in this release.