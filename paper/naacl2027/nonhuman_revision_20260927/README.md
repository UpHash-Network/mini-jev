# September 27 manuscript and evidence-guide revision

This revision accompanies the nine-page conference-preparation manuscript:
six pages of main text/disclosures, two pages of references, and one appendix.
It has not been submitted to NAACL, accepted, or peer reviewed. The separately
submitted arXiv source remains unchanged and is awaiting moderation.

- [Manuscript PDF](../NAACL2027_Mini_Jev.pdf)
- [Reviewer guide and model-free checks](REVIEWER_GUIDE.md)
- [Post-hoc LMQL diagnostic](lmql_diagnostic/README.md)
- [Related-work comparison](../RELATED_WORK_COMPARISON.20260927.md)
- [Revision record (Japanese)](REVISION.ja.md)
- [Publication file manifest](PUBLICATION_MANIFEST.json)

The revision corrects the public inspection scope: typed values, candidate
probabilities, and semantic metadata are exposed by the public API/UI; candidate
token IDs and raw logits are internal engine/research-trace data. The appendix
distinguishes matched numerical comparisons, integration diagnostics, and
primary-source feature comparisons. The LMQL post-hoc analysis retains all
three failures of the original probability tolerance. It uses the same logs,
not new model calls. No human usability result is claimed.

The frozen source/evidence ZIP, original framework diagnostic records, submitted
arXiv artifacts, abstract, and original experiment numbers are preserved.
`CHECKS.json` and `EVIDENCE_CHECKS.json` record the preparation-stage checks;
`push_performed: false` in the former describes that earlier point in time.
Publication edits subsequently updated documentation status and links without
changing the reviewed PDF or experimental records. `PUBLICATION_MANIFEST.json`
records the current distribution hashes and intentionally excludes itself.
The containing Git commit supplies the immutable publication identifier.

The claim audit is a historical review of the pre-correction manuscript; its
line numbers and quoted wording refer to that version. It mentions an internally
retained AI fixture rehearsal, which is not included in this release and does
not contribute evidence of human performance or model quality.
