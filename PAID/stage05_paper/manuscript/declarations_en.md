# Declarations

*Draft. To be completed with author and funding information before submission.*

## Data availability

The frozen analysis-ready data and derived artefacts required to audit and reproduce the reported analyses have been prepared as the PAID Reviewer Reproducibility Package v1.2.1 and will be deposited at {{DATA_ARCHIVE_DOI}}; during peer review they will be accessible through {{DATA_REVIEWER_LINK}}. The release contains the complete 32,748-cell Shenzhen spatial split and the exact frozen analysis-ready covariate and land-surface-temperature tables used for Regions A, B and C, together with the candidate registries, Stage-04 evaluation artefacts, Stage-05 benchmark outputs, figure-source data and protocol-audit records. The complete Region-C analysis-ready table is provided solely for reproducibility of the locked-region evaluation. Region C is scientifically spent under Protocol V1 and must not be interpreted as an independent or pristine confirmatory holdout. The approximately 857-MB original Shenzhen source-raster archive is not included in the core release because redistribution rights and source metadata are incomplete; instead, the exact frozen analysis-ready values used in the manuscript and a source-data provenance inventory are provided. Changchun row-level analysis-ready data are distributed only to the extent permitted by the applicable third-party data terms; where redistribution is not permitted, the archive provides the analysis code, schema, provenance, hashes and derived outputs.

## Code availability

The code required to audit and reproduce the frozen analyses reported in this study has been prepared for release at {{CODE_REPOSITORY_URL}} and will be archived at {{CODE_ARCHIVE_DOI}} under release {{RELEASE_TAG}} (commit {{CODE_COMMIT_SHA}}). The archive preserves the historical PAID Stage 00–05 implementation together with a portable reviewer-verification layer. The portable layer verifies the frozen spatial partition, candidate hashes, Region-C Stage-04 statistics, the R=25 sensitivity analysis, Stage-05 conventional baselines, the external-replication outputs where the associated data may be redistributed, figure-source artefacts and release manifests without relying on the original local directory structure or the historical AES key. Historical scripts are retained for provenance and are not retrospectively altered. Verification and recomputation of the published numerical results from the frozen release artefacts require no LLM or network access. The role of any LLM in workflow development or scientific decision-making is described separately in the AI-usage disclosure and MODEL_AND_AGENT_DISCLOSURE.md.

## AI usage disclosure

The scientific discovery and validation pipeline reported in this study was executed as deterministic Python software. Large-language-model tools were used during workflow development and manuscript authoring, but no language-model service was called by the archived scientific execution pipeline at run time. Candidate evaluation, model fitting, spatial validation, permutation tests, bootstrap inference and all reported numerical results are reproducible from the released code, frozen data and random seeds without language-model or network access.

## Ethics

The study uses publicly derived urban environmental data and involves no human or animal subjects.

## Author contributions

To be completed (CRediT).

## Competing interests

The authors declare no competing interests.

## Funding

To be completed.

## Acknowledgements

To be completed.
