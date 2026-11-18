# Machine learning: PyTorch, scikit-learn, tracking, evaluation

Builds on `python.md` and `dataframes.md`. Verified November 2026 on PyPI: PyTorch 2.15, scikit-learn 1.9, MLflow 3.18, DVC 3.67, skops 0.16. Check current versions on `https://pypi.org/project/<name>/`.

## Reproducibility

- Every hyperparameter, path and seed lives in a typed, frozen config loaded from a committed file. No literals in training code.
- Record with each run: config, seed, git commit, `uv.lock` hash, data version (DVC, Delta/Iceberg snapshot or file hash).
- Pass a `numpy.random.Generator` around; never use the global NumPy RNG.

```python
@dataclass(frozen=True, slots=True)
class TrainConfig:
    seed: int
    learning_rate: float
    batch_size: int
    max_epochs: int
    data_version: str


def seed_everything(seed: int) -> np.random.Generator:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    return np.random.default_rng(seed)
```

- On CUDA, deterministic algorithms need `CUBLAS_WORKSPACE_CONFIG=:4096:8` in the environment. Pass `generator=` to `DataLoader` and seed workers with `worker_init_fn`.

## scikit-learn

- Put all preprocessing in a `Pipeline` with a `ColumnTransformer`, so it is fitted on training folds only (no leakage).
- Set `random_state` on every estimator and splitter that takes one.
- Split by how data arrives: `StratifiedKFold` for imbalance, `GroupKFold` when rows share an entity, `TimeSeriesSplit` for time. Touch the test set once, at the end.

```python
features: ColumnTransformer = ColumnTransformer(
    [("numeric", StandardScaler(), NUMERIC_COLUMNS),
     ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS)]
)
pipeline: Pipeline = Pipeline(
    [("features", features),
     ("model", LogisticRegression(max_iter=MAX_ITERATIONS, random_state=config.seed))]
)
folds: StratifiedKFold = StratifiedKFold(
    n_splits=FOLD_COUNT, shuffle=True, random_state=config.seed
)
scores: dict[str, np.ndarray] = cross_validate(
    pipeline, train_features, train_target, cv=folds, scoring=SCORING
)
```

## PyTorch

- `model.train()` for training, `model.eval()` plus `torch.inference_mode()` for evaluation and serving.
- Device and precision (`torch.autocast`) come from config. Annotate tensors and modules (`torch.Tensor`, `nn.Module`).
- Checkpoints save `state_dict`, optimizer state, epoch and config. Load with `torch.load(path, weights_only=True)`.
- Never unpickle a model from an untrusted source. Use safetensors for weights, skops for scikit-learn models.

## Experiment tracking

- MLflow (or the team's tracker): one run per config; log params, metrics per epoch, the model and the data version.
- Never log secrets, raw personal data or sample predictions on personal data. Review what autologging captures before enabling it.

## Evaluation

- Compare against a baseline (`DummyClassifier`, last production model). Choose metrics from the cost of errors; report per-slice metrics and bootstrap confidence intervals, not one number.
- Tune thresholds and hyperparameters on validation data, never on test data.

## Tests

- Unit-test feature code as pure functions (see `dataframes.md`). Model tests: output shape and dtype; one batch overfits to near-zero loss; same seed gives identical output; invariance (irrelevant change keeps prediction) and directional checks.
- CI regression gate: a small pinned evaluation set where the metric must stay above a named threshold.
