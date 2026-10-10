"""Train reproducible demo model on synthetic data or a compatible labelled CSV."""
from pathlib import Path
import argparse, json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
FEATURES = ['sample_LDR', 'ambient_LDR', 'reflectance_ratio']
TARGET = 'shade_label'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data/demo_data_simulated.csv')
    args = ap.parse_args()
    path = Path(args.data)
    if not path.is_absolute(): path = ROOT / path
    df = pd.read_csv(path)
    required = FEATURES + [TARGET]
    missing = [c for c in required if c not in df.columns]
    if missing: raise SystemExit(f'Missing columns: {missing}. Required: {required}')
    df = df.dropna(subset=required).copy()
    if 'specimen_id' not in df.columns:
        raise SystemExit('CSV must include specimen_id so repeated readings can be split without leakage.')
    X, y, groups = df[FEATURES], df[TARGET].astype(str), df['specimen_id']
    split = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=117)
    tr, te = next(split.split(X, y, groups))
    model = Pipeline([('scaler', StandardScaler()), ('classifier', RandomForestClassifier(
        n_estimators=150, class_weight='balanced', random_state=117))])
    model.fit(X.iloc[tr], y.iloc[tr])
    pred = model.predict(X.iloc[te])
    accuracy = float(accuracy_score(y.iloc[te], pred))
    macro_f1 = float(f1_score(y.iloc[te], pred, average='macro'))
    bundle = {'pipeline': model, 'features': FEATURES, 'classes': list(model.named_steps['classifier'].classes_),
              'training_min': {c: float(X.iloc[tr][c].min()) for c in FEATURES},
              'training_max': {c: float(X.iloc[tr][c].max()) for c in FEATURES},
              'data_source': 'SIMULATED' if set(df.get('data_source', pd.Series(['UNKNOWN'])).astype(str)) == {'SIMULATED'} else 'USER_SUPPLIED',
              'training_seed': 117, 'target': TARGET}
    joblib.dump(bundle, ROOT / 'shade_model.joblib')
    (ROOT / 'outputs' / 'classification_report.txt').write_text(
        'DATA SOURCE: ' + bundle['data_source'] + '\n'
        + f'Accuracy: {accuracy:.4f}\nMacro-F1: {macro_f1:.4f}\n\n'
        + classification_report(y.iloc[te], pred, zero_division=0), encoding='utf-8')
    cm = confusion_matrix(y.iloc[te], pred, labels=bundle['classes'])
    pd.DataFrame(cm, index=bundle['classes'], columns=bundle['classes']).to_csv(ROOT / 'outputs' / 'confusion_matrix.csv')
    summary = {'data_source': bundle['data_source'], 'accuracy': accuracy, 'macro_f1': macro_f1,
               'features': FEATURES, 'classes': bundle['classes'], 'training_min': bundle['training_min'],
               'training_max': bundle['training_max'], 'split': 'specimen_id grouped 75/25',
               'warning': 'Synthetic-data metrics are software checks only, not real-world performance.'}
    (ROOT / 'outputs' / 'evaluation_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f"Trained model saved: {ROOT / 'shade_model.joblib'}")
    print(f"Data source: {bundle['data_source']} | accuracy={accuracy:.3f} | macro-F1={macro_f1:.3f}")
    print('These metrics apply only to this dataset. Do not claim real-world accuracy from simulated data.')
    print('Training ranges:')
    for c in FEATURES: print(f"  {c}: {bundle['training_min'][c]:.4f} .. {bundle['training_max'][c]:.4f}")

if __name__ == '__main__': main()
