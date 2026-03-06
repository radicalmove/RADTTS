"""Project scaffolding and path management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .constants import DEFAULT_PRESETS
from .models import now_utc_iso


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    assets_source_audio: Path
    assets_reference_audio: Path
    assets_generated_audio: Path
    transcripts: Path
    captions: Path
    manifests: Path


class ProjectManager:
    def __init__(self, projects_root: Path | str = Path("projects")):
        self.projects_root = Path(projects_root)

    def list_projects(self) -> list[str]:
        if not self.projects_root.exists():
            return []

        project_ids: list[str] = []
        for entry in self.projects_root.iterdir():
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") or entry.name.startswith("_"):
                continue
            project_ids.append(entry.name)
        return sorted(project_ids)

    def project_root(self, project_id: str) -> Path:
        return self.projects_root / project_id

    def get_paths(self, project_id: str) -> ProjectPaths:
        root = self.project_root(project_id)
        return ProjectPaths(
            root=root,
            assets_source_audio=root / "assets" / "source_audio",
            assets_reference_audio=root / "assets" / "reference_audio",
            assets_generated_audio=root / "assets" / "generated_audio",
            transcripts=root / "transcripts",
            captions=root / "captions",
            manifests=root / "manifests",
        )

    def create_project(
        self,
        project_id: str,
        *,
        course: str | None = None,
        module: str | None = None,
        lesson: str | None = None,
    ) -> ProjectPaths:
        paths = self.get_paths(project_id)
        for folder in (
            paths.assets_source_audio,
            paths.assets_reference_audio,
            paths.assets_generated_audio,
            paths.transcripts,
            paths.captions,
            paths.manifests,
        ):
            folder.mkdir(parents=True, exist_ok=True)

        metadata = {
            "project_id": project_id,
            "course": course,
            "module": module,
            "lesson": lesson,
            "created_at": now_utc_iso(),
            "updated_at": now_utc_iso(),
        }
        self._write_json(paths.manifests / "project.json", metadata)

        for manifest_file in ("jobs.json", "outputs.json"):
            path = paths.manifests / manifest_file
            if not path.exists():
                self._write_json(path, [])

        presets_path = paths.manifests / "presets.json"
        if not presets_path.exists():
            self._write_json(presets_path, DEFAULT_PRESETS)

        return paths

    def ensure_project(self, project_id: str) -> ProjectPaths:
        paths = self.get_paths(project_id)
        if not paths.root.exists():
            raise FileNotFoundError(
                f"Project '{project_id}' does not exist at {paths.root}. Run create-project first."
            )
        return paths

    @staticmethod
    def _write_json(path: Path, data: object) -> None:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
