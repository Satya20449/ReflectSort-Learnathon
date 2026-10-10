"""
DUMMY model generator - for TESTING the integration only.
Member 2's real model replaces shade_model.joblib. Data here is SYNTHETIC,
so any accuracy from this model must NOT be reported as a project result.
"""
import random
import joblib
from sklearn.tree import DecisionTreeClassifier
from shade_demo import make_features

random.seed(0)
X, y = [], []
for label, lo, hi in (("BIN_A", 0.15, 0.35), ("BIN_B", 0.5, 0.7), ("BIN_C", 0.9, 1.1)):
    for _ in range(60):
        ref = random.randint(1700, 1900)
        amb = random.randint(300, 700)
        smp = int(ref * random.uniform(lo, hi))
        X.append(make_features(smp, amb, ref))
        y.append(label)

model = DecisionTreeClassifier(max_depth=4, random_state=0).fit(X, y)
joblib.dump(model, "shade_model.joblib")
print("Saved DUMMY shade_model.joblib (synthetic data, testing only)")
