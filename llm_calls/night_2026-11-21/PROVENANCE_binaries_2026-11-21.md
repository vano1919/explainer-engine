# Provenance of the binaries used tonight (2026-11-21)

Gitignored, not committed. Recorded so the origin of every file used by a test or a local render is known.

| File | Size | sha256 | Origin | Licence | How it was obtained |
|---|---|---|---|---|---|
| tools/depth/depth_anything_v2_small.onnx | 99 MB | afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c | onnx-community/depth-anything-v2-small (Hugging Face), model.onnx | Apache-2.0 (per explainer_engine/production/depth.py) | downloaded tonight by the depth setup; hash above is of the file on disk |
| tools/maps/SR_HR.tif | 233 MB | 18d7e9171f860abd1108a5ac064946d15ad9b5b68d0644e97194e47ee4e93f5a | Natural Earth shaded relief, fetched by explainer_engine/production/relief_fetch.py | public domain (Natural Earth terms) | fetched tonight by relief_fetch; the file is larger than the 44 MB in the module docstring, so the fetched version differs from what the docstring says and should be checked |

Not checked tonight: that the on-disk ONNX hash matches the upstream Hugging Face revision (no revision pinned in depth.py).
No PR 256 binary was touched here; BINARY_CHECK_PR256.md covers those.
