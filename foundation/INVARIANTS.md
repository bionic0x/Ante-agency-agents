# Invariants and the tests that hold them

Each invariant of the foundation is demonstrated by at least one test that fails
if the invariant is broken. Test names are in `tests/foundation/` unless stated.

| # | Invariant | Tests |
|---|---|---|
| 1 | Authority is not a YAML field; outputs are `PROCEED`, `PROCEED_WITH_CONDITIONS`, `HOLD`, `REDESIGN`, `REJECT`; doubt or incomplete evidence gives `HOLD` | `test_strategy`: `test_example_chain_runs_end_to_end` (the record states it grants no authority), `test_pending_evidence_caps_at_hold`, `test_a_plan_metric_without_misuse_analysis_cannot_pass_the_interactive_test`; `test_develop`: `test_a_clean_patch_without_held_out_evidence_holds`; `test_core`: `test_enums_come_from_contracts_json` |
| 2 | Epistemic states are distinct; `ATTRIBUTED_INTENT` separates capability from will and rises to `EVIDENCE` only through an observation that could have refuted it | `test_strategy`: `test_attributed_intent_separates_capability_from_will`, `test_attributed_intent_rises_only_through_a_refuting_observation`, `test_repetition_of_the_same_source_is_not_observation`, `test_a_proper_upgrade_is_accepted` |
| 3 | Self-development never changes the protected evaluator | `test_develop`: `test_protected_and_out_of_scope_paths_are_refused_before_any_gate`, `test_a_forged_proposal_cannot_bring_its_own_evaluator`, `test_the_loop_never_opens_a_pull_request_touching_github`, the Turing lock tests; `test_learn`: `test_learn_cannot_write_into_a_construct`; `test_package`: `test_moves_are_mechanical` |
| 4 | The improver never sees held-out evidence | `test_develop`: `test_held_out_packs_inside_the_checkout_are_refused`, `test_an_injected_canary_rejects_the_proposal`; `test_ice`: canary seeding and scanning, `test_the_checkout_itself_carries_no_canary` |
| 5 | v1 compatibility: same CLI, exit codes and bytes | `tests/characterization/run.py` (114 cases recorded at the base commit); `foundation/tools/extraction.py verify`; `test_package`: `test_every_moved_module_imports_as_a_package_module` |
| 6 | Nothing new opens the network by default | `test_invariants`: `test_no_module_imports_a_network_library`, `test_only_declared_modules_start_processes`, `test_the_whole_chain_learning_and_deck_run_with_sockets_disabled`, `test_a_dry_run_pull_request_starts_no_process`; `test_runbooks_and_drafts`: `test_model_is_explicit_and_provider_declared` |
| 7 | No self-intoxication: system artefacts never count as independent corroboration | `test_strategy`: `test_system_output_cannot_be_evidence`, `test_shared_sources_count_once_and_system_output_is_excluded`; `test_learn`: `test_system_sources_cannot_confirm_or_refute`; `test_second_line`: `test_discarded_material_is_archived_with_its_reason_and_returns_only_as_hypothesis`; `test_runbooks_and_drafts`: `test_draft_forces_hypothesis_and_cannot_be_chained` |
| 8 | No fabricated metrics: `null` with a reason | `test_learn`: `test_below_the_minimum_the_answer_is_insufficient_sample`, `test_synthetic_decisions_never_enter_calibration`, `test_without_reconciled_decisions_nothing_is_learned`, `test_adoption_needs_history`; `test_strategy`: `test_rows_come_from_the_doctrine_and_gaps_are_published` |
| 9 | Chapter XVII stays in quarantine: its conjectures support nothing and block nothing | `test_invariants`: `test_doctrine_tables_hold_seven_tests_and_fourteen_pathologies_only`, `test_no_check_cites_chapter_xvii` |
| 10 | Independence is declared honestly; only `INDEPENDENT_OPERATOR` satisfies VIII.9 | `test_strategy`: `test_proceed_needs_an_independent_review`, `test_review_commands_declare_independence`; `test_develop`: `test_reviews_by_the_loop_by_a_lower_level_for_another_proposal_or_forged_are_refused` |

What these tests cannot show: that a declared `INDEPENDENT_OPERATOR` really is
independent, that a human owner really holds the authority a record names, or
that held-out packs kept outside the checkout were never read by the person
running the improver. Those remain organisational facts the code records but
cannot verify.
