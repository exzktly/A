# Processed-image filename suffix migration plan

## Problem statement

Current output writing in `process_microscopy_v2.py` (around lines 772-805) derives a single `base_name` from the nuclear image stem and then emits channel-encoded suffixes such as:

- `_tophat_nir.tif`
- `_tophat_<fluor_token>.tif`
- `_smfish_<fluor_token>.tif`

This conflicts with the desired naming rule:

- For each processed image, output filename should be:
  - `input_stem + processing_suffix + original_extension`
- Example:
  - input: `A01_w1594_T01.tif`
  - output top-hat: `A01_w1594_T01_tophat.tif`

## Implementation plan

1. Introduce a shared filename builder in `process_microscopy_v2.py`.
   - Signature shape:
     - `build_processed_name(src_path: Path, suffix: str, ext_override: str | None = None) -> str`
   - Behavior:
     - uses `src_path.stem`
     - appends suffix exactly once
     - preserves input extension unless an explicit override is required

2. Replace per-output naming in `process_image_group` to be input-based.
   - Nuclear top-hat output:
     - from `nuclear_path`, suffix `_tophat`
   - Fluor top-hat output (per channel):
     - from matching `fluor_paths[i]`, suffix `_tophat`
   - smFISH output (per smFISH channel):
     - from matching `fluor_paths[i]`, suffix `_smfish`
   - Labels and overlays remain derived from the nuclear image:
     - `_labels`
     - `_overlay` (with png extension where intended)
   - Watershed auxiliary artifacts tied to segmentation should keep suffix-only semantics on the nuclear stem:
     - `_nuclear_points`
     - `_cytoplasm_tophat`
     - `_cytoplasm_otsu_mask`

3. Add a compatibility option for downstream consumers.
   - Add a CLI/config switch such as `--legacy_channel_suffix_naming` (default `false`).
   - When enabled, preserve old `_tophat_<channel>` / `_smfish_<channel>` behavior to avoid breaking older archives and workflows.

4. Update logging messages to print output names actually written.
   - This simplifies post-run validation and debugging of naming policy.

## Functional impact on image-consuming/display code

### 1) Viewer filename resolution (high impact)

`well_viewer/image_resolver.py` currently recognizes channel-encoded processed suffixes:

- tophat: `"_tophat_{channel}.tif"`
- smfish: `"_smfish_{channel}.tif"`

With new naming, resolver must also support channel-agnostic processed suffixes:

- `"_tophat.tif"`
- `"_smfish.tif"`

Resolution should prioritize exact channel-encoded matches first (for legacy sets), then fallback to channel-agnostic names mapped by frame key extraction.

### 2) Filename candidate generation and policy tests (high impact)

`tests/test_filename_resolver_policy.py` and related resolver tests currently assert candidate endings like `_tophat_gfp.tif` and `_smfish_gfp.tif`.

These tests should be expanded (or migrated) to cover:

- new canonical endings (`_tophat.tif`, `_smfish.tif`)
- legacy endings retained under compatibility mode
- precedence behavior when both formats coexist in the same archive

### 3) Any regex-based filename classification in preview/montage (medium impact)

Where preview logic identifies processed fluor assets by regex patterns containing `_tophat_<token>`, update to allow both naming families.

### 4) Documentation and operator expectations (medium impact)

Update user docs to describe:

- new naming policy
- compatibility flag behavior
- migration expectations for existing zip outputs

## Rollout and verification plan

1. Implement dual-resolution support in viewer first.
2. Add writer compatibility flag and new default naming in pipeline.
3. Add tests for both naming schemes.
4. Run UI smoke checks on mixed datasets:
   - legacy-only
   - new-only
   - mixed-format zip
5. Deprecate legacy naming in a later release after warning period.
