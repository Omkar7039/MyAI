import json
from pathlib import Path

from core.model import LocalModel
from project.patch_set import PatchSet
from project.patch_validator import PatchValidator


class MultiFileRepairPlanner:
    """
    Convert a ChangePlan + grounded evidence into a validated PatchSet.

    No files are modified here.
    """

    def __init__(self, model=None, root="~/MyAI"):
        self.model = model or LocalModel()
        self.root = Path(root).expanduser().resolve()
        self.validator = PatchValidator(self.root)

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

            "The original field MUST exactly match the current file."
        )

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
