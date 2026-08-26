"""Multi-class (normal/dos/probe/r2l/u2r) model construction — Milestone 4.

The winner of this milestone becomes the PRODUCTION pipeline: per ADR-012 the
M5 /predict endpoint serves the multi-class model only (prediction = "attack"
iff category != "normal").

Each candidate is one sklearn Pipeline = shared M2 preprocessor + classifier
(ADR-005), with the scaling variant its model family needs
(docs/preprocessing-decisions.md §8). Configurations are sensible defaults,
not tuned — hyperparameter search stays out of scope, same rule as M3.
"""

from scipy import sparse
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from src.config import RANDOM_STATE
from src.preprocessing import build_preprocessor

MULTICLASS_MODEL_NAMES = (
    "logistic_regression", "random_forest", "hist_gradient_boosting",
)

# Presentation order for reports/confusion matrices: majority class first,
# then attacks from most to least frequent. (sklearn itself orders classes_
# alphabetically; evaluation always passes labels explicitly.)
CATEGORY_ORDER = ("normal", "dos", "probe", "r2l", "u2r")


def densify(X):
    """Convert the preprocessor's sparse output to a dense array.

    HistGradientBoostingClassifier requires dense input. A module-level named
    function (not a lambda) so joblib can serialize the pipeline (ADR-009) —
    same rule as restore_su_attempted_domain. ~100k rows x 121 features of
    float64 is ~97 MB, well within reach.
    """
    return X.toarray() if sparse.issparse(X) else X


def build_multiclass_pipeline(model_name):
    """Return an unfitted Pipeline(preprocessor -> classifier) for one model.

    logistic_regression: native multinomial (softmax) linear model; needs
        standardized numerics. max_iter raised for convergence, as in M3.
    random_forest: 100-tree ensemble, natively multi-class (leaf counts over
        all 5 classes); raw numeric units, scale-invariant.
    hist_gradient_boosting: sklearn-native gradient boosting (LightGBM-style
        histogram trees), natively multi-class (one tree per class per
        boosting round). Defaults include early_stopping='auto', which on
        >10k rows reserves a seeded 10% of the TRAINING split to pick the
        iteration count — training-data-only, so no protocol violation.
    """
    if model_name == "logistic_regression":
        scaling = "standard"
        steps = [("classifier",
                  LogisticRegression(max_iter=1000, random_state=RANDOM_STATE))]
    elif model_name == "random_forest":
        scaling = "none"
        steps = [("classifier", RandomForestClassifier(
            n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1))]
    elif model_name == "hist_gradient_boosting":
        scaling = "none"
        steps = [
            ("densify", FunctionTransformer(densify)),
            ("classifier",
             HistGradientBoostingClassifier(random_state=RANDOM_STATE)),
        ]
    else:
        raise ValueError(
            f"model_name must be one of {MULTICLASS_MODEL_NAMES}, "
            f"got {model_name!r}"
        )
    return Pipeline([("preprocessor", build_preprocessor(scaling=scaling)),
                     *steps])
