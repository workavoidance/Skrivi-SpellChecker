# Recovered Norwegian spelling sandbox

Run **Start-Skrivi.cmd** for the responsive interface; **Start-Wordnet-Experiment.cmd** enables optional wider word help. Keep the launcher window open while using the browser.

Normal launch reuses `%LOCALAPPDATA%\Skrivi` or `SKRIVI_CACHE_DIR`, with no downloads. On another computer install Python 3.12 x64 and run **Setup-Once.cmd**. Optional WordNet requires **Setup-Wordnet-Experiment.cmd** once. Norwegian Windows speech requires an installed Norwegian voice. Fresh-machine setup has not been revalidated during recovery.

Write, press **Sjekk teksten**, and choose corrections individually. Copy important writing before closing; drafts are not automatically saved. Exported trial results contain writing and should remain private.

Source was recovered without algorithm changes; see `../docs/RECOVERY-MANIFEST.json`. Historical experiment scripts are included, but their datasets/results remain in the ignored local recovery snapshot. Their presence does not mean they are active in the normal interface. The older English/Qwen prototype remains only in that snapshot.

## Optional candidate coverage

Restart the normal launcher and select **Flere ordforslag (utprøving)** to try extra possessive and compound suggestions. The existing default stays selected. This option also appears in the WordNet interface. It requires the already-cached Ordbank and frequency databases; when missing, the option is disabled. It downloads nothing. See [measurements and limitations](../docs/benchmarks/2026-09-24-coverage-integration.md).
