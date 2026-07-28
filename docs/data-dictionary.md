# NSL-KDD Data Dictionary

Filled during Milestone 1 EDA (2026-07-28), verified against the actual files —
not copied from a website. Stats refer to KDDTrain+ (125,973 rows) unless noted.

**What is one row?** One *flow* — a summary of a complete connection between two
machines (like describing a whole phone call: who called, how long, how much was
said — rather than recording every word). The 41 features fall into four groups:

1. **Basic** (1–9): from packet headers — protocol, bytes, duration.
2. **Content** (10–22): from payloads — logins, shell access, file operations.
   These exist to catch R2L/U2R attacks that look normal at the header level.
3. **Time-based traffic** (23–31): counts over the **last 2 seconds** — catches
   fast attacks (DoS floods, port scans).
4. **Host-based traffic** (32–41): counts over the **last 100 connections** to the
   same destination — catches slow attacks that spread activity over minutes.

## Basic features

| # | Column | Type | Meaning | Why it matters for detection | Model input? |
|---|--------|------|---------|------------------------------|--------------|
| 1 | `duration` | int (s) | Length of the connection. Median 0, max 42,908 | Long idle connections can indicate tunnels; scans are near-instant | ✅ |
| 2 | `protocol_type` | cat (3) | `tcp`, `udp`, `icmp` | Some attacks are protocol-specific (e.g. smurf uses ICMP) | ✅ one-hot |
| 3 | `service` | cat (70) | Destination service, e.g. `http`, `ftp`, `telnet` | Attacks target specific services; rare services are suspicious | ✅ one-hot |
| 4 | `flag` | cat (11) | TCP connection status, e.g. `SF` (normal open+close), `S0` (no reply), `REJ` (rejected) | Floods of `S0`/`REJ` are the signature of SYN floods and scans | ✅ one-hot |
| 5 | `src_bytes` | int | Bytes from source → destination. Max 1.38 **billion** | Huge = possible exfiltration; 0 with many connections = scanning | ✅ |
| 6 | `dst_bytes` | int | Bytes destination → source | Asymmetry between the two directions characterizes many attacks | ✅ |
| 7 | `land` | 0/1 | Source and destination address+port identical | Only true for the "land" DoS attack (rare: 0.02% of rows) | ✅ |
| 8 | `wrong_fragment` | int | Count of malformed packet fragments | Fragmentation abuse = teardrop-style DoS | ✅ |
| 9 | `urgent` | int | Packets with the TCP URG flag set | Legitimate traffic almost never uses it | ✅ |

## Content features (catch R2L / U2R)

| # | Column | Type | Meaning | Why it matters | Model input? |
|---|--------|------|---------|----------------|--------------|
| 10 | `hot` | int | Count of "hot" indicators (entering system directories, running programs) | Direct sign of someone poking around after entry | ✅ |
| 11 | `num_failed_logins` | int | Failed login attempts | Password guessing (R2L) | ✅ |
| 12 | `logged_in` | 0/1 | Login succeeded in this connection (40% of rows) | Context for the other content features | ✅ |
| 13 | `num_compromised` | int | "Compromised" conditions observed | Post-intrusion activity | ✅ |
| 14 | `root_shell` | 0/1 | A root shell was obtained | Strong U2R signal | ✅ |
| 15 | `su_attempted` | 0/1/2 | `su root` was attempted | Privilege-escalation attempt (U2R) | ✅ |
| 16 | `num_root` | int | Operations performed as root | Post-escalation activity | ✅ |
| 17 | `num_file_creations` | int | File creation operations | Dropping payloads/backdoors | ✅ |
| 18 | `num_shells` | int | Shell prompts opened | Interactive intruder activity | ✅ |
| 19 | `num_access_files` | int | Writes to access-control files (e.g. `/etc/passwd`) | Tampering with authentication | ✅ |
| 20 | `num_outbound_cmds` | int | Outbound commands in an FTP session | **Constant 0 in the entire dataset — dropped in Milestone 2 (zero information)** | ❌ drop |
| 21 | `is_host_login` | 0/1 | Login belongs to a privileged "host" list | Only 1 positive row in 126k — nearly dead | ✅ (kept, harmless to trees) |
| 22 | `is_guest_login` | 0/1 | Logged in as guest/anonymous | Guest access is a common R2L entry point | ✅ |

## Time-based traffic features (2-second window)

| # | Column | Type | Meaning | Why it matters | Model input? |
|---|--------|------|---------|----------------|--------------|
| 23 | `count` | int | Connections to the **same host** in the past 2 s (mean 84, max 511) | High = flood or scan in progress | ✅ |
| 24 | `srv_count` | int | Connections to the **same service** in the past 2 s | Bursts against one service = DoS/probe signature | ✅ |
| 25 | `serror_rate` | rate 0–1 | % of those connections with SYN errors (`S0`-style: no reply) | ~1.0 during SYN floods and stealth scans | ✅ |
| 26 | `srv_serror_rate` | rate | Same, per-service | As above, service-scoped | ✅ |
| 27 | `rerror_rate` | rate | % with REJ (rejected) errors | High = knocking on closed doors = scanning | ✅ |
| 28 | `srv_rerror_rate` | rate | Same, per-service | As above | ✅ |
| 29 | `same_srv_rate` | rate | % of recent connections to the same service | Near 1.0 = hammering one service | ✅ |
| 30 | `diff_srv_rate` | rate | % to *different* services | High = sweeping across services = probe | ✅ |
| 31 | `srv_diff_host_rate` | rate | % of same-service connections going to different hosts | High = one service probed across many machines | ✅ |

## Host-based traffic features (last 100 connections to the same destination)

Same ideas as the 2-second window, but over a longer horizon so **slow** attacks
can't hide by pacing themselves.

| # | Column | Type | Meaning | Model input? |
|---|--------|------|---------|--------------|
| 32 | `dst_host_count` | int (≤255) | Connections to this destination host | ✅ |
| 33 | `dst_host_srv_count` | int (≤255) | ...to the same service on that host | ✅ |
| 34 | `dst_host_same_srv_rate` | rate | % to the same service | ✅ |
| 35 | `dst_host_diff_srv_rate` | rate | % to different services (slow probes) | ✅ |
| 36 | `dst_host_same_src_port_rate` | rate | % reusing the same source port (scripted traffic) | ✅ |
| 37 | `dst_host_srv_diff_host_rate` | rate | % same-service from different sources (distributed activity) | ✅ |
| 38 | `dst_host_serror_rate` | rate | SYN-error % at host scope | ✅ |
| 39 | `dst_host_srv_serror_rate` | rate | SYN-error % at service scope | ✅ |
| 40 | `dst_host_rerror_rate` | rate | REJ % at host scope | ✅ |
| 41 | `dst_host_srv_rerror_rate` | rate | REJ % at service scope | ✅ |

## Target and metadata columns

| Column | Meaning | Model input? |
|---|---|---|
| `label` | Raw label: `normal` or a specific attack name (`neptune`, `smurf`, ...) | ❌ target source |
| `difficulty` | NSL-KDD authors' score: how many of their 21 reference classifiers got this row right | ❌ dropped (leaks evaluation info) |
| `is_attack` *(derived)* | 0 = normal, 1 = attack — binary target (FR2) | ❌ target |
| `category` *(derived)* | `normal` / `dos` / `probe` / `r2l` / `u2r` — multi-class target (FR3) | ❌ target |

## Key EDA findings (verified 2026-07-28)

1. **Binary classes are nearly balanced** (train: 53.5% normal / 46.5% attack) —
   accuracy isn't meaningless for the binary task, but per-class metrics still matter.
2. **Category imbalance is extreme:** train has 45,927 DoS rows but only **52 U2R**
   rows. U2R recall will be poor; this is a data property, not a bug (risk R7).
3. **Distribution shift is deliberate:** 17 attack types appear *only* in the test
   set, and R2L jumps from 0.8% of train to 12.2% of test. Test scores will look
   worse than validation scores — that's the benchmark testing generalization.
4. **No unseen categorical values in test** (`protocol_type`, `service`, `flag` are
   all covered by train), so one-hot encoding fit on train is safe.
5. **`num_outbound_cmds` is constant zero** → dropped in Milestone 2.
6. **Feature scales span 9 orders of magnitude** (`src_bytes` max 1.38B vs rate
   features in [0,1]) → scaling required for any distance/gradient-based model.
