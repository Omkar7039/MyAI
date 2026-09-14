from dataclasses import dataclass, field


@dataclass
class FilePatch:
    file: str
    original: str
    updated: str
    reason: str = ""

    @property
    def changed(self):
        return self.original != self.updated


@dataclass
class PatchSet:
    request: str
    patches: list[FilePatch] = field(default_factory=list)

    @property
    def files_changed(self):
        return [
            patch.file
            for patch in self.patches
            if patch.changed
        ]

    @property
    def count(self):
        return len(self.files_changed)

    def add(
        self,
        file: str,
        original: str,
        updated: str,
        reason: str = "",
    ):
        self.patches.append(
            FilePatch(
                file=file,
                original=original,
                updated=updated,
                reason=reason,
            )
        )

    def validate(self):
        errors = []

        seen = set()

        for patch in self.patches:
            if patch.file in seen:
                errors.append(
                    f"Duplicate patch for file: {patch.file}"
                )

            seen.add(patch.file)

            if not patch.file:
                errors.append(
                    "Patch file path is empty."
                )

            if patch.original == patch.updated:
                errors.append(
                    f"No changes detected: {patch.file}"
                )

        return errors

    def summary(self):
        return {
            "request": self.request,
            "files_changed": self.files_changed,
            "count": self.count,
            "validation_errors": self.validate(),
        }
