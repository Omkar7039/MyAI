import json
from pathlib import Path

from core.model import LocalModel
from project.patch_set import PatchSet
from project.patch_validator import PatchValidator
from experience.project_link_store import ExperienceProjectLinkStore
from experience.store import ExperienceStore
from experience.retriever import ExperienceRetriever


class MultiFileRepairPlanner:
    """
    Convert a ChangePlan + grounded evidence into a validated PatchSet.

    No files are modified here.
    """

    def __init__(self, model=None, root="~/MyAI"):
        self.model = model or LocalModel()
        self.root = Path(root).expanduser().resolve()
        self.validator = PatchValidator(self.root)
        self.experience_link_store = ExperienceProjectLinkStore(
            self.root / "data" / "experience.db"
        )
        self.experience_store = ExperienceStore(
            self.root / "data" / "experience.db"
        )
        self.experience_retriever = ExperienceRetriever(
            self.experience_store
        )

    def build_patch_set(
        self,
        request: str,
        plan,
        evidence: str,
        model_response=None,
    ):
        """
        Build a validated PatchSet.

        model_response is optional and is primarily useful for deterministic
        testing without invoking the local model.
        """

        if model_response is None:
            prompt = self._build_prompt(
                request=request,
                plan=plan,
                evidence=evidence,
            )

            model_response = self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=384,
            )

        data = self._parse_response(
            model_response
        )

        if data is None:
            return {
                "success": False,
                "patch_set": None,
                "errors": [
                    "Model did not return valid JSON."
                ],
                "warnings": [],
                "raw_response": model_response,
            }

        patch_set = PatchSet(
            request=request
        )

        authorized_files = set(
            plan.affected_files
        )

        for item in data.get("patches", []):
            if not isinstance(item, dict):
                continue

            file_path = item.get("file")
            original = item.get("original")
            updated = item.get("updated")
            reason = item.get("reason", "")

            if not all(
                isinstance(value, str)
                for value in [
                    file_path,
                    original,
                    updated,
                ]
            ):
                continue

            # A model may inspect many files, but it is not allowed to
            # propose changes outside the ChangePlan impact scope.
            if file_path not in authorized_files:
                continue

            patch_set.add(
                file=file_path,
                original=original,
                updated=updated,
                reason=reason,
            )

        if not patch_set.patches:
            return {
                "success": False,
                "patch_set": None,
                "errors": [
                    "No authorized patches were returned."
                ],
                "warnings": [],
                "raw_response": model_response,
            }

        validation = self.validator.validate(
            patch_set
        )

        if not validation["valid"]:
            return {
                "success": False,
                "patch_set": patch_set,
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "raw_response": model_response,
            }

        return {
            "success": True,
            "patch_set": patch_set,
            "errors": [],
            "warnings": validation["warnings"],
            "raw_response": model_response,
        }

    def _build_prompt(
        self,
        request,
        plan,
        evidence,
    ):
        targets = "\n".join(
            f"- {target.file}:{target.symbol}"
            for target in plan.targets
        )

        affected = "\n".join(
            f"- {file_path}"
            for file_path in plan.affected_files
        )

        dependencies = "\n".join(
            f"- {value}"
            for value in plan.dependencies
        )

        flow = "\n".join(
            f"- {value}"
            for value in plan.flow
        )

        experience = self._collect_experience(
            request=request,
            plan=plan,
            max_results=4,
            max_chars=1800,
        )

        return (
            "You are MyAI's multi-file repair planner.\n\n"
            "Return ONLY valid JSON.\n"
            "Do not use markdown.\n"
            "Do not execute commands.\n"
            "Do not modify files.\n"
            "Do not invent files.\n"
            "Only propose changes to AUTHORIZED FILES.\n"
            "Keep changes as small as possible.\n\n"

            "JSON FORMAT:\n"
            "{\n"
            '  "patches": [\n'
            "    {\n"
            '      "file": "relative/path.py",\n'
            '      "original": "exact current file content",\n'
            '      "updated": "complete updated file content",\n'
            '      "reason": "why the change is required"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"

            f"USER REQUEST:\n{request}\n\n"

            "AUTHORIZED TARGET SYMBOLS:\n"
            f"{targets or '- none'}\n\n"

            "AUTHORIZED FILES:\n"
            f"{affected or '- none'}\n\n"

            "DEPENDENCIES:\n"
            f"{dependencies or '- none'}\n\n"

            "VERIFIED RESOLVED FLOW:\n"
            f"{flow or '- none'}\n\n"

            "GROUNDED EVIDENCE:\n"
            f"{evidence}\n\n"

            "HISTORICAL EXPERIENCE:\n"
            f"{experience}\n\n"

            "The historical experience is advisory only. "
            "Current source code, requirements, and verification results are authoritative.\n\n"

            "The original field MUST exactly match the current file."
        )

    def _collect_experience(
        self,
        request,
        plan,
        max_results=4,
        max_chars=1800,
    ):
        # Retrieve project-linked experience as advisory repair context.
        candidates = {}

        for link in self.experience_link_store.search_project(
            str(self.root),
            limit=50,
        ):
            candidates[link.experience_id] = link

        for target in plan.targets:
            for link in self.experience_link_store.search_symbol(
                target.symbol,
                limit=50,
            ):
                if link.project_root == str(self.root):
                    candidates[link.experience_id] = link

        for file_path in plan.affected_files:
            for link in self.experience_link_store.search_file(
                file_path,
                limit=50,
            ):
                if link.project_root == str(self.root):
                    candidates[link.experience_id] = link

        if not candidates:
            return 'No project-linked historical experience found.'

        ranked = self.experience_retriever.search(
            request,
            limit=max_results,
            include_failures=True,
        )

        linked = [
            item
            for item in ranked
            if item.experience.experience_id in candidates
        ]

        if not linked:
            return 'No relevant project-linked historical experience found.'

        lines = [
            'Project-linked history is advisory only.',
        ]
        used = len(lines[0]) + 1

        for item in linked:
            exp = item.experience
            block = (
                f'- Task: {exp.task}\n'
                f'  Action: {exp.action}\n'
                f'  Outcome: {exp.outcome}\n'
                f'  Lesson: {exp.lesson}\n'
            )

            if used + len(block) > max_chars:
                break

            lines.append(block)
            used += len(block)

        return '\n'.join(lines)[:max_chars]
    def _parse_response(self, response):
        if not response:
            return None

        text = response.strip()

        try:
            value = json.loads(text)

            if isinstance(value, dict):
                return value

        except json.JSONDecodeError:
            pass

        if "```" in text:
            parts = text.split("```")

            for part in parts:
                candidate = part.strip()

                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()

                try:
                    value = json.loads(candidate)

                    if isinstance(value, dict):
                        return value

                except json.JSONDecodeError:
                    continue

        return None
