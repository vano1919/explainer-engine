"""Reverse-Engineered Studio Elements Vault (LTX Studio ``Elements`` / Google Flow ``Ingredients``).

Maintains persistent, SHA-256-pinned visual anchors for ``@Character``, ``@Location``,
``@Prop``, and ``@Style`` across an entire film so every storyboard panel and video shot
reuses visual evidence rather than drifting via text-only re-description.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VALID_ELEMENT_KINDS = frozenset({"character", "location", "prop", "style"})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(slots=True)
class StudioElement:
    element_id: str
    kind: str
    display_name: str
    canonical_traits: str
    anchor_image: str = ""
    anchor_sha256: str = ""
    voice_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ElementsVault:
    """Persistent studio asset registry enforcing visual-evidence anchoring across every shot."""

    def __init__(self, project_id: str, style_directive: str) -> None:
        self.project_id = project_id
        self.style_directive = style_directive.strip()
        self.elements: dict[str, StudioElement] = {}

    def register(
        self,
        *,
        element_id: str,
        kind: str,
        display_name: str,
        canonical_traits: str,
        anchor_image: Path | str | None = None,
        voice_id: str = "",
        extra: dict[str, Any] | None = None,
    ) -> StudioElement:
        if kind not in VALID_ELEMENT_KINDS:
            raise ValueError(f"Unsupported element kind {kind!r}; expected one of {sorted(VALID_ELEMENT_KINDS)}")
        img_str = ""
        img_sha = ""
        if anchor_image is not None:
            p = Path(anchor_image)
            if not p.is_file():
                raise FileNotFoundError(f"Element anchor image not found: {p}")
            img_str = str(p.resolve())
            img_sha = _sha256_file(p)
        el = StudioElement(
            element_id=element_id,
            kind=kind,
            display_name=display_name,
            canonical_traits=canonical_traits.strip(),
            anchor_image=img_str,
            anchor_sha256=img_sha,
            voice_id=voice_id,
            extra=dict(extra or {}),
        )
        self.elements[element_id] = el
        return el

    def resolve_reference_images(self, element_ids: list[str], *, max_refs: int = 3) -> list[str]:
        """Return up to ``max_refs`` anchor image paths (matches chat ``generate_image`` 3-image cap)."""
        refs: list[str] = []
        for eid in element_ids:
            el = self.elements.get(eid)
            if el and el.anchor_image and el.anchor_image not in refs:
                refs.append(el.anchor_image)
            if len(refs) >= max_refs:
                break
        return refs

    def build_anchored_shot_prompt(
        self,
        *,
        element_ids: list[str],
        single_action: str,
        framing: str,
        camera_lens: str = "35mm anamorphic prime, shallow depth of field",
        lighting_override: str = "",
    ) -> dict[str, Any]:
        """Compose a Runway/LTX-Studio disciplined prompt: visual evidence for identity, text for 1 action."""
        tagged_traits: list[str] = []
        for eid in element_ids:
            el = self.elements.get(eid)
            if not el:
                raise KeyError(f"Unknown studio element_id: {eid!r}")
            tagged_traits.append(f"@{el.element_id} ({el.display_name}): {el.canonical_traits}")

        parts = [
            f"CAMERA & FRAMING: {framing}, shot on {camera_lens}.",
            f"LOCKED ELEMENTS (preserve exact visual identity, set architecture, and wardrobe from reference images): {' | '.join(tagged_traits)}.",
            f"SINGLE PRIMARY ACTION: {single_action.strip()}.",
            f"LIGHTING & FILM STYLE: {lighting_override.strip() or self.style_directive}.",
            "STRICT PHOTOREALISM: real 35mm documentary cinema film still, natural skin pores, breath vapor, zero CGI plastic sheen, zero text or watermarks.",
        ]
        return {
            "prompt": " ".join(parts),
            "reference_images": self.resolve_reference_images(element_ids, max_refs=3),
            "element_ids": list(element_ids),
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "studio_elements_vault/1",
            "project_id": self.project_id,
            "style_directive": self.style_directive,
            "elements": {k: v.to_dict() for k, v in self.elements.items()},
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> ElementsVault:
        raw = json.loads(path.read_text(encoding="utf-8"))
        vault = cls(raw["project_id"], raw["style_directive"])
        for k, v in (raw.get("elements") or {}).items():
            vault.elements[k] = StudioElement(**v)
        return vault
