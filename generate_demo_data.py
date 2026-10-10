"""Reproducibly generate SIMULATED ReflectSort training data. Not real sensor data."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'demo_data_simulated.csv'
SEED = 117

def main():
    rng = np.random.default_rng(SEED)
    rows = []
    # Synthetic class bands chosen only to exercise the software pipeline.
    # They are not calibrated optical measurements and must not be used to claim real accuracy.
    bands = {'Dark': (1.45, 2.35), 'Medium': (2.65, 3.75), 'Light': (4.10, 5.65)}
    for shade, (lo, hi) in bands.items():
        for specimen in range(100):
            # Per-specimen latent value and repeat readings emulate clustered observations.
            latent_ratio = rng.uniform(lo, hi)
            specimen_id = f'{shade.upper()}_{specimen:03d}'
            for rep in range(3):
                ambient = int(rng.integers(130, 166))
                ratio = max(1.05, latent_ratio + rng.normal(0, 0.045))
                sample = int(round(ambient * ratio + rng.normal(0, 5)))
                sample = int(np.clip(sample, 1, 4095))
                rows.append({'specimen_id': specimen_id, 'run_id': rep + 1,
                             'sample_LDR': sample, 'ambient_LDR': ambient,
                             'reflectance_ratio': sample / ambient, 'shade_label': shade,
                             'data_source': 'SIMULATED'})
    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f'Wrote {len(df)} SIMULATED rows to {OUT}')
    print('Reminder: synthetic data only; not a substitute for physical sensor measurements.')

if __name__ == '__main__': main()
