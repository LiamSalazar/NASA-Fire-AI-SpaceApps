# Immutable LUCI development regression fixture

NASA NTRS [20250010653](https://ntrs.nasa.gov/citations/20250010653), publicly downloadable original PDF, 2,906,408 bytes, SHA-256 `bb0aadd2f9543483467b86796e6aa19f4e13c3f8169eec96134015f95ed61d79`.

This deliberately selected original document and its original v1 submission payload make source-integrity and saved-output replay tests reproducible without an API key or an ignored SQLite database. The six failure payloads were exported without modification from `v1/holdout_first_pass/workspace/data/index/evidence.sqlite` (read-only). Only two contain normalized partial proposals; none contains original raw provider response bytes. Missing bytes have not been reconstructed.

LUCI is a development/regression investigation. These fixtures do not represent unseen evaluation, successful live inference, independent expert adjudication or accepted scientific knowledge. Synthetic adapter responses are labeled in their tests. The original v1/v2 execution files remain unchanged.
