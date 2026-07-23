# Native output-filter benchmark corpus

The corpus is deterministic, synthetic, offline, and authored for ai-toolkit.
It measures pure profile transformation separately from hook process startup.

The gates are 20 ms p95 for inputs up to 100 KiB, 150 ms p95 for the 8 MiB
hard-cap case, at least 30% reduction, and peak traced allocation no greater
than three input sizes plus 16 MiB. The cold-process gate invokes the production
Bash wrapper with a fresh Python process for every sample in one native session;
its p95 limit is 75 ms. The default 100 samples keep the p95 gate stable enough
for release validation.
