"""Central configuration: paths, dataset schema, and attack category mapping.

Every other module imports from here so there is exactly one place where
file locations and column definitions live (development standard: no magic
values scattered through the code).
"""

from pathlib import Path

# --- Paths ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

TRAIN_FILE = DATA_RAW / "KDDTrain+.txt"
TEST_FILE = DATA_RAW / "KDDTest+.txt"

# --- Reproducibility ------------------------------------------------------

# Project-wide random seed (Milestone-1 review must-fix). Every stochastic
# step in M2-M4 — train/validation splits, cross-validation, model seeds —
# must use this value so results are reproducible run-to-run.
RANDOM_STATE = 42

# --- Dataset schema ------------------------------------------------------

# NSL-KDD files have no header row. These are the 41 features in file order,
# followed by the attack label and a "difficulty" score added by the NSL-KDD
# authors (how many of their 21 reference classifiers got the row right).
COLUMN_NAMES = [
    # basic connection features (from packet headers)
    "duration", "protocol_type", "service", "flag",
    "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
    # content features (from packet payloads, e.g. login attempts)
    "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login",
    # time-based traffic features (same host/service in last 2 seconds)
    "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate",
    # host-based traffic features (last 100 connections to same destination)
    "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate",
    "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
    # target + metadata
    "label", "difficulty",
]

CATEGORICAL_FEATURES = ["protocol_type", "service", "flag"]

# --- Attack category mapping ---------------------------------------------

# NSL-KDD labels rows with specific attack names (e.g. "neptune", "smurf").
# We group them into the 4 standard categories. The test set intentionally
# contains attack types that never appear in training — those are included
# here too so evaluation can map them.
ATTACK_CATEGORIES = {
    # DoS — flood a machine so real users can't use it
    "back": "dos", "land": "dos", "neptune": "dos", "pod": "dos",
    "smurf": "dos", "teardrop": "dos", "apache2": "dos", "udpstorm": "dos",
    "processtable": "dos", "mailbomb": "dos",
    # Probe — scan a network to find weaknesses before attacking
    "ipsweep": "probe", "nmap": "probe", "portsweep": "probe",
    "satan": "probe", "mscan": "probe", "saint": "probe",
    # R2L (Remote-to-Local) — outsider gains access to a machine
    "ftp_write": "r2l", "guess_passwd": "r2l", "imap": "r2l",
    "multihop": "r2l", "phf": "r2l", "spy": "r2l", "warezclient": "r2l",
    "warezmaster": "r2l", "sendmail": "r2l", "named": "r2l",
    "snmpgetattack": "r2l", "snmpguess": "r2l", "xlock": "r2l",
    "xsnoop": "r2l", "worm": "r2l",
    # U2R (User-to-Root) — normal user illegally becomes administrator
    "buffer_overflow": "u2r", "loadmodule": "u2r", "perl": "u2r",
    "rootkit": "u2r", "httptunnel": "u2r", "ps": "u2r",
    "sqlattack": "u2r", "xterm": "u2r",
}


def label_to_category(label: str) -> str:
    """Map a raw NSL-KDD label to 'normal', 'dos', 'probe', 'r2l' or 'u2r'."""
    if label == "normal":
        return "normal"
    if label in ATTACK_CATEGORIES:
        return ATTACK_CATEGORIES[label]
    raise ValueError(f"Unknown attack label: {label!r}")
