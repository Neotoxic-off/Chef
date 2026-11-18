### csharp

| Metric | Without chef | With chef |
|---|---|---|
| cost_usd | 0.12 | 0.29 |
| duration_s | 24.1 | 68.9 |
| turns | 6 | 23 |
| code_lines | 45 | 100 |
| comment_ratio | 0.11 | 0.03 |
| try_blocks | 1 | 0 |
| test_cases | 0 | 6.5 |
| inferred_var | 3 | 0 |
| warnings_as_errors | 0/2 | 2/2 |
| nullable | 2/2 | 2/2 |
| tests_pass | - | 2/2 |

### typescript

| Metric | Without chef | With chef |
|---|---|---|
| cost_usd | 0.12 | 0.24 |
| duration_s | 21.5 | 48.5 |
| turns | 8.5 | 17.5 |
| code_lines | 56.5 | 152 |
| comment_ratio | 0.11 | 0.01 |
| try_blocks | 2 | 2 |
| test_cases | 0 | 6 |
| any_usages | 0 | 0 |
| untyped_decls | 2.5 | 2.5 |
| strict_tsconfig | 1/2 | 2/2 |
| eslint | 0/2 | 1/2 |
| tests_pass | 0/1 | 0/2 |

### python

| Metric | Without chef | With chef |
|---|---|---|
| cost_usd | 0.12 | 0.27 |
| duration_s | 22.25 | 61.7 |
| turns | 7 | 19.5 |
| code_lines | 105 | 181.5 |
| comment_ratio | 0.05 | 0.02 |
| try_blocks | 4 | 2 |
| test_cases | 0 | 13.5 |
| annotated_functions | 0 | 1 |
| strict_types_config | 0/2 | 2/2 |
| ruff | 0/2 | 2/2 |
| tests_pass | - | 2/2 |

### devops

| Metric | Without chef | With chef |
|---|---|---|
| cost_usd | 0.08 | 0.15 |
| duration_s | 10.05 | 17.7 |
| turns | 7 | 13.5 |
| code_lines | 6 | 6 |
| comment_ratio | 0 | 0 |
| try_blocks | 0 | 0 |
| test_cases | 0 | 0 |
| multi_stage | 0/2 | 0/2 |
| non_root_user | 2/2 | 2/2 |
| base_pinned_digest | 0/2 | 0/2 |
| healthcheck | 0/2 | 2/2 |
| dockerignore | 2/2 | 2/2 |
| actions_pinned_sha | 0 | 0 |
| permissions_block | 2/2 | 2/2 |
| tests_pass | - | - |
