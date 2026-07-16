"""Tunable constants shared across the pipeline. Kept in one place so a
teammate can find every knob without hunting through the pipeline modules."""
import os

# Optional path to a local copy of the real AIOps2020 challenge dataset (the
# `2020_MM_DD/...` folder tree). If set and it exists, `source=dataset`
# regenerates alerts live from the real metrics via app/data/aiops_loader.py
# instead of using the bundled sample_loghub.csv slice. Unset by default --
# the dataset is multi-gigabyte and not part of this repo.
AIOPS_RAW_DATASET_ROOT = os.environ.get("NUCLEUS_AIOPS_DATASET_ROOT")

# Sliding window sizing for the correlation pipeline. Overlapping windows
# (step < window) guarantee an incident that straddles a window boundary
# still has both halves seen together at least once; the cross-window
# union-find merge in clustering.py stitches the resulting local clusters
# back into one global cluster.
WINDOW_SECONDS = 1200.0  # 20 minutes
STEP_SECONDS = 600.0    # 10 minutes (50% overlap)

# HDBSCAN parameters. min_cluster_size=5 means "root cause + at least 4
# symptoms" is the smallest thing we call an incident; smaller groups fall
# out as noise/standalone alerts instead. This is the floor that keeps
# min_samples=1 (single-linkage-like, chains aggressively) from fabricating
# "incidents" out of a couple of coincidentally-similar background alerts --
# we tested min_cluster_size=2-3 during tuning and it does exactly that
# (pairs of unrelated noise alerts forming their own pure-noise "clusters"),
# which is worse than the reduction% it buys. cluster_selection_epsilon
# merges sibling sub-clusters that split apart below this distance --
# without it, one incident's alerts on slightly different services/wording
# fragment into several small clusters instead of one correlated incident.
#
# These four values (+ DEFAULT_ALPHA/BETA/GAMMA below) were grid-searched
# to maximize reduction_pct on both the synthetic set (validated against its
# ground-truth incident labels: zero incidents merged together, zero
# pure-noise clusters) and the real bundled AIOps2020 slice (validated
# structurally: zero clusters spanning more than one real host) at the same
# time -- settings that only looked good on one dataset (e.g. min_cluster_
# size=2 hit 98%+ reduction on synthetic data alone) turned out to merge
# unrelated real hosts together, so they were rejected despite the higher
# number. See backend/scripts/tune_reduction.py to reproduce or re-run this
# search after changing the generator or the distance metric.
MIN_CLUSTER_SIZE = 5
MIN_SAMPLES = 1
CLUSTER_SELECTION_EPSILON = 0.2

# Cross-window merges (see pipeline/clustering.py _DisjointSet) are rejected
# if they'd stretch a cluster's total time span beyond this many seconds.
# Without this cap, a long chain of coincidentally-similar background alerts
# strung end-to-end across many overlapping windows can transitively bridge
# two genuinely unrelated incidents into one giant cluster -- each individual
# merge looks locally reasonable, but the transitive closure isn't. Capping
# the span enforces "a single incident's blast radius is bounded," which is
# true of real incidents and lets us safely reject unbounded chaining.
MAX_INCIDENT_SPAN_SECONDS = 3600.0  # 60 minutes

# Fixed normalizer for temporal_distance (see pipeline/distance.py): alerts
# more than this many seconds apart are treated as maximally distant in time
# (distance 1.0), regardless of window size. This must be a fixed constant
# rather than "max gap observed in this window" -- otherwise the same
# absolute time gap would score differently depending on what else happened
# to fall in the current window, which breaks the "normalized 0-1" contract.
# 900s (15 min) comfortably covers our synthetic incidents' ~7-8 min blast
# radius while still discriminating against unrelated background alerts.
TEMPORAL_NORMALIZER_SECONDS = 900.0

# Default composite-distance weights, used when the API caller omits them.
# Temporal + service-topology proximity carry more weight than raw semantic
# similarity by default: within one real incident, symptom wording varies a
# lot ("circuit breaker OPEN" vs "replica lag increasing") even though the
# alerts are clearly the same cascading failure, whereas "happened within
# minutes, on a directly-dependent service" is a much more reliable signal
# that they belong together. Moving alpha up favors tight semantic matches
# (more, smaller, wording-pure clusters); moving beta/gamma up favors
# recognizing a broader cascade as one incident.
DEFAULT_ALPHA = 0.15  # semantic
DEFAULT_BETA = 0.55   # temporal
DEFAULT_GAMMA = 0.3   # service-topology

# Synthetic generator defaults (used for /api/alerts/raw and .../correlated).
SYNTHETIC_SEED = 42
SYNTHETIC_NUM_INCIDENTS = 8
SYNTHETIC_TARGET_TOTAL = 800
SYNTHETIC_DURATION_HOURS = 6.0
