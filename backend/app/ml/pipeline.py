"""Laptop-Friendly Dynamometer Card Classification Pipeline.

Pipelines:
  Raw card points -> normalization & resampling -> EFD + geometric features -> SVM classifier.
  Benchmark comparison: RandomForest / XGBoost.
  Labeling: SYNTHETIC-DEMO VALIDATION.
"""

from typing import List, Tuple, Dict, Any, Optional
import os
import json
import joblib
import numpy as np

from sklearn.model_selection import StratifiedKFold, train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .features import (
    extract_card_features,
    explain_geometric_reasons,
    resample_card_points,
    normalize_card_points,
    elliptic_fourier_descriptors,
    extract_interpretable_features,
)
from .stress_indicator import (
    evaluate_rod_stress_screening,
    RodStressConfig,
    RodStressScreeningResult,
)


class CardClassifier:
    """Laptop-friendly SVM card classifier with EFD and engineered features."""

    def __init__(self, models_dir: str = "data/models"):
        self.models_dir = models_dir
        self.model: Optional[SVC] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: List[str] = []
        self.classes: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.is_loaded = False
        self._try_load()

    def _try_load(self) -> bool:
        """Attempt to load pre-trained model and scaler if available."""
        model_path = os.path.join(self.models_dir, "card_classifier_svm.joblib")
        scaler_path = os.path.join(self.models_dir, "scaler.joblib")
        cfg_path = os.path.join(self.models_dir, "feature_config.json")
        metrics_path = os.path.join(self.models_dir, "metrics.json")

        if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(cfg_path):
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.feature_names = cfg.get("feature_names", [])
                    self.classes = cfg.get("classes", [])

                if os.path.exists(metrics_path):
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        self.metrics = json.load(f)

                self.is_loaded = True
                return True
            except Exception:
                self.is_loaded = False
                return False
        return False

    def train_and_evaluate(
        self,
        dataset_npz_path: str = "data/synthetic/dynamometer_cards.npz",
        output_dir: Optional[str] = None,
        random_seed: int = 42,
        cv_folds: int = 5,
        test_size: float = 0.20,
    ) -> Dict[str, Any]:
        """Train primary SVM and benchmark secondary models on synthetic dataset.

        Produces:
          - Trained SVM model and StandardScaler
          - Feature config and metrics JSON (with SYNTHETIC-DEMO VALIDATION label)
          - Confusion matrix visualization PNG
        """
        out_dir = output_dir or self.models_dir
        os.makedirs(out_dir, exist_ok=True)

        if not os.path.exists(dataset_npz_path):
            raise FileNotFoundError(f"Synthetic dataset not found at {dataset_npz_path}")

        data = np.load(dataset_npz_path)
        surface_cards = data["surface_cards"]  # Shape (N, 100, 2)
        labels = data["labels"]                # Shape (N,)
        n_samples = len(labels)

        # 1. Feature extraction for all cards
        feature_matrix: List[np.ndarray] = []
        feature_names_list: List[str] = []

        for i in range(n_samples):
            pts = surface_cards[i]
            vec, _, f_names = extract_card_features(pts.tolist(), target_num_points=100, num_harmonics=10)
            feature_matrix.append(vec)
            if not feature_names_list:
                feature_names_list = f_names

        X = np.array(feature_matrix, dtype=np.float64)
        y = np.array(labels)
        unique_classes = sorted(list(set(y)))

        # 2. Stratified Train/Test Split (fixed seed, no leakage)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_seed, stratify=y
        )

        # 3. Scaling
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # 4. Cross-Validation & Model Selection for SVM (RBF vs Linear)
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_seed)

        svm_rbf = SVC(kernel="rbf", C=5.0, probability=True, random_state=random_seed)
        svm_linear = SVC(kernel="linear", C=1.0, probability=True, random_state=random_seed)

        cv_scores_rbf = cross_val_score(svm_rbf, X_train_scaled, y_train, cv=skf, scoring="accuracy")
        cv_scores_linear = cross_val_score(svm_linear, X_train_scaled, y_train, cv=skf, scoring="accuracy")

        best_kernel = "rbf" if np.mean(cv_scores_rbf) >= np.mean(cv_scores_linear) else "linear"
        primary_svm = svm_rbf if best_kernel == "rbf" else svm_linear

        # Fit best SVM on full training set
        primary_svm.fit(X_train_scaled, y_train)

        # 5. Evaluate on Hold-Out Test Set
        y_pred = primary_svm.predict(X_test_scaled)
        test_acc = float(accuracy_score(y_test, y_pred))
        prec, rec, f1, support = precision_recall_fscore_support(
            y_test, y_pred, labels=unique_classes, zero_division=0
        )
        macro_prec = float(np.mean(prec))
        macro_rec = float(np.mean(rec))
        macro_f1 = float(np.mean(f1))

        cm = confusion_matrix(y_test, y_pred, labels=unique_classes)

        per_class_metrics = {}
        for idx, cls in enumerate(unique_classes):
            per_class_metrics[cls] = {
                "precision": round(float(prec[idx]), 4),
                "recall": round(float(rec[idx]), 4),
                "f1_score": round(float(f1[idx]), 4),
                "support": int(support[idx]),
            }

        # 6. Secondary Benchmark: RandomForest & XGBoost
        benchmark_results = {}

        rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=random_seed)
        rf_cv = cross_val_score(rf, X_train, y_train, cv=skf, scoring="accuracy")
        rf.fit(X_train, y_train)
        rf_test_acc = float(accuracy_score(y_test, rf.predict(X_test)))
        benchmark_results["random_forest"] = {
            "cv_accuracy_mean": round(float(np.mean(rf_cv)), 4),
            "test_accuracy": round(rf_test_acc, 4),
            "params": {"n_estimators": 100, "max_depth": 8},
        }

        try:
            from xgboost import XGBClassifier
            # Map labels to integers for XGBoost
            label_to_int = {c: i for i, c in enumerate(unique_classes)}
            y_train_int = np.array([label_to_int[l] for l in y_train])
            y_test_int = np.array([label_to_int[l] for l in y_test])

            xgb = XGBClassifier(
                n_estimators=80,
                max_depth=4,
                learning_rate=0.1,
                random_state=random_seed,
                eval_metric="mlogloss",
            )
            xgb.fit(X_train, y_train_int)
            xgb_pred = xgb.predict(X_test)
            xgb_test_acc = float(accuracy_score(y_test_int, xgb_pred))
            benchmark_results["xgboost"] = {
                "test_accuracy": round(xgb_test_acc, 4),
                "params": {"n_estimators": 80, "max_depth": 4},
            }
        except Exception as e:
            benchmark_results["xgboost"] = {"status": f"skipped: {str(e)}"}

        # 7. Render and Save Confusion Matrix Plot
        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
        ax.figure.colorbar(im, ax=ax)
        ax.set(
            xticks=np.arange(cm.shape[1]),
            yticks=np.arange(cm.shape[0]),
            xticklabels=unique_classes,
            yticklabels=unique_classes,
            title="Confusion Matrix: Card Classifier\n[SYNTHETIC-DEMO VALIDATION]",
            ylabel="True Prototype Class",
            xlabel="Predicted Class",
        )
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right", rotation_mode="anchor")

        # Loop over data dimensions and create text annotations
        thresh = cm.max() / 2.0
        for r in range(cm.shape[0]):
            for c in range(cm.shape[1]):
                ax.text(
                    c, r, format(cm[r, c], "d"),
                    ha="center", va="center",
                    color="white" if cm[r, c] > thresh else "black",
                    fontweight="bold",
                )
        fig.tight_layout()
        cm_image_path = os.path.join(out_dir, "confusion_matrix.png")
        fig.savefig(cm_image_path, dpi=180, bbox_inches="tight")
        plt.close(fig)

        # 8. Save Artifacts
        model_save_path = os.path.join(out_dir, "card_classifier_svm.joblib")
        scaler_save_path = os.path.join(out_dir, "scaler.joblib")
        cfg_save_path = os.path.join(out_dir, "feature_config.json")
        metrics_save_path = os.path.join(out_dir, "metrics.json")

        joblib.dump(primary_svm, model_save_path)
        joblib.dump(scaler, scaler_save_path)

        feature_config_dict = {
            "feature_names": feature_names_list,
            "classes": unique_classes,
            "num_harmonics": 10,
            "target_num_points": 100,
            "selected_kernel": best_kernel,
            "num_features": len(feature_names_list),
        }
        with open(cfg_save_path, "w", encoding="utf-8") as f:
            json.dump(feature_config_dict, f, indent=2)

        # Assemble full metrics payload with strict SYNTHETIC-DEMO VALIDATION notice
        metrics_payload = {
            "validation_badge": "SYNTHETIC-DEMO VALIDATION",
            "provenance_note": (
                "Validation metrics evaluated strictly on synthetic numerical-wave & analytical "
                "dynamometer cards. No real-world field accuracy is asserted or claimed."
            ),
            "primary_model": {
                "algorithm": "Support Vector Classifier (SVC)",
                "kernel": best_kernel,
                "cv_accuracy_rbf_mean": round(float(np.mean(cv_scores_rbf)), 4),
                "cv_accuracy_linear_mean": round(float(np.mean(cv_scores_linear)), 4),
                "test_accuracy": round(test_acc, 4),
                "macro_precision": round(macro_prec, 4),
                "macro_recall": round(macro_rec, 4),
                "macro_f1": round(macro_f1, 4),
            },
            "per_class_metrics": per_class_metrics,
            "confusion_matrix": cm.tolist(),
            "secondary_benchmarks": benchmark_results,
            "training_summary": {
                "total_samples": n_samples,
                "train_samples": len(y_train),
                "test_samples": len(y_test),
                "num_classes": len(unique_classes),
                "random_seed": random_seed,
            },
            "artifact_paths": {
                "model": model_save_path,
                "scaler": scaler_save_path,
                "feature_config": cfg_save_path,
                "confusion_matrix": cm_image_path,
            },
        }

        with open(metrics_save_path, "w", encoding="utf-8") as f:
            json.dump(metrics_payload, f, indent=2)

        # Update in-memory state
        self.model = primary_svm
        self.scaler = scaler
        self.feature_names = feature_names_list
        self.classes = unique_classes
        self.metrics = metrics_payload
        self.is_loaded = True

        return metrics_payload

    def predict_condition(
        self,
        card_points: List[Tuple[float, float]],
        rod_diameter_in: float = 0.875,
        stress_config: Optional[RodStressConfig] = None,
    ) -> Dict[str, Any]:
        """Predict well condition from raw card points with confidence, alternatives, and geometric reasons.

        Returns:
            Dict containing:
              - class: predicted prototype CardClass
              - probability: float confidence
              - top_alternatives: List of {"class": str, "probability": float}
              - key_geometric_reasons: List of explanatory strings
              - stress_screening: RodStressScreeningResult
              - features: Dictionary of extracted interpretable features
              - validation_badge: "SYNTHETIC-DEMO VALIDATION"
        """
        if not self.is_loaded:
            loaded = self._try_load()
            if not loaded:
                # Run self-training on synthetic dataset if available
                dataset_path = "data/synthetic/dynamometer_cards.npz"
                if os.path.exists(dataset_path):
                    self.train_and_evaluate(dataset_path)
                else:
                    raise RuntimeError("Model is not loaded and no synthetic training dataset is available.")

        # 1. Feature extraction
        vec, interp_dict, _ = extract_card_features(
            card_points, target_num_points=100, num_harmonics=10
        )

        # 2. Scale features
        vec_scaled = self.scaler.transform(vec.reshape(1, -1))

        # 3. Model prediction and class probabilities
        probs = self.model.predict_proba(vec_scaled)[0]
        pred_idx = int(np.argmax(probs))
        pred_class = self.classes[pred_idx]
        confidence = float(probs[pred_idx])

        # 4. Top alternatives
        sorted_indices = np.argsort(probs)[::-1]
        alternatives = [
            {"class": self.classes[idx], "probability": round(float(probs[idx]), 4)}
            for idx in sorted_indices if idx != pred_idx
        ]

        # 5. Key geometric explanations
        reasons = explain_geometric_reasons(interp_dict, pred_class)

        # 6. Rod-load stress screening evaluation
        peak_load = interp_dict.get("peak_load_lbf", 10000.0)
        min_load = interp_dict.get("min_load_lbf", 2000.0)
        s_cfg = stress_config or RodStressConfig(rod_diameter_in=rod_diameter_in)
        stress_screening = evaluate_rod_stress_screening(
            peak_load_lbf=peak_load,
            min_load_lbf=min_load,
            config=s_cfg,
        )

        return {
            "class": pred_class,
            "probability": round(confidence, 4),
            "top_alternatives": alternatives,
            "key_geometric_reasons": reasons,
            "stress_screening": stress_screening.to_dict(),
            "features": {k: round(v, 4) if isinstance(v, float) else v for k, v in interp_dict.items()},
            "validation_badge": "SYNTHETIC-DEMO VALIDATION",
        }


# Global singleton instance for quick access
_classifier_instance: Optional[CardClassifier] = None


def get_card_classifier(models_dir: str = "data/models") -> CardClassifier:
    """Get or create singleton CardClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = CardClassifier(models_dir=models_dir)
    return _classifier_instance


def predict_condition(
    card_points: List[Tuple[float, float]],
    rod_diameter_in: float = 0.875,
    stress_config: Optional[RodStressConfig] = None,
) -> Dict[str, Any]:
    """Top-level convenience API for dynamometer card condition diagnosis."""
    classifier = get_card_classifier()
    return classifier.predict_condition(
        card_points=card_points,
        rod_diameter_in=rod_diameter_in,
        stress_config=stress_config,
    )
