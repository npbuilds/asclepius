"""v1.5.2 BioBERT training pipeline.

Offline tooling — runs at training time, not at runtime. The output of this
pipeline (parquet of (features, criteria_text, label) tuples + a separate
embeddings.npy after the BioBERT pass) feeds the gradient-boosted-trees
classifier whose pickled artifact ends up at
api/app/modules/ml_pos_prior/model.joblib.

Pipeline stages:
  1. download_hint.sh           — fetch HINT corpus to api/data/hint/
  2. build_training_dataset.py  — CSV → parquet with structured features +
                                  criteria text + outcome label
  3. (future) embed_biobert.py  — parquet → embeddings.npy
  4. (future) train_gbt.py      — combined features → model.joblib
"""
