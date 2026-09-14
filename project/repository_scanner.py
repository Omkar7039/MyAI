from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileInfo:
    path: str
    extension: str
    language: str
    size_bytes: int
    is_test: bool
    is_config: bool


@dataclass
class RepositoryReport:
    root: str
    total_files: int = 0
    total_bytes: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    files: list[FileInfo] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)


class RepositoryScanner:
    IGNORED_DIRECTORIES = {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "target",
    }

    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".sh": "bash",
        ".bash": "bash",
        ".sql": "sql",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".R": "r",
    }

    CONFIG_NAMES = {
        ".env",
        ".env.example",
        ".gitignore",
        ".dockerignore",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Makefile",
        "CMakeLists.txt",
        "tsconfig.json",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        "mypy.ini",
        ".pre-commit-config.yaml",
    }

    DEPENDENCY_NAMES = {
        "requirements.txt",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "pyproject.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "go.mod",
        "go.sum",
        "Cargo.toml",
        "Cargo.lock",
        "Gemfile",
        "Gemfile.lock",
        "composer.json",
    }

    def scan(self, root: str | Path):
        root_path = Path(root).expanduser().resolve()

        if not root_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {root_path}"
            )

        if not root_path.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {root_path}"
            )

        report = RepositoryReport(
            root=str(root_path)
        )

        for path in root_path.rglob("*"):
            if not path.is_file():
                continue

            if self._is_ignored(path, root_path):
                continue

            try:
                size = path.stat().st_size
            except OSError:
                continue

            relative = path.relative_to(root_path)

            extension = path.suffix.lower()
            language = self.LANGUAGE_MAP.get(
                extension,
                "other",
            )

            is_test = self._is_test_file(path)
            is_config = self._is_config_file(path)

            info = FileInfo(
                path=str(relative),
                extension=extension,
                language=language,
                size_bytes=size,
                is_test=is_test,
                is_config=is_config,
            )

            report.files.append(info)
            report.total_files += 1
            report.total_bytes += size

            report.languages[language] = (
                report.languages.get(language, 0) + 1
            )

            if is_test:
                report.test_files.append(str(relative))

            if is_config:
                report.config_files.append(str(relative))

            if path.name in self.DEPENDENCY_NAMES:
                report.dependency_files.append(
                    str(relative)
                )

        return report

    def _is_ignored(
        self,
        path: Path,
        root: Path,
    ):
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            return True

        return any(
            part in self.IGNORED_DIRECTORIES
            for part in relative_parts
        )

    def _is_test_file(self, path: Path):
        name = path.name.lower()

        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.js")
            or name.endswith(".spec.js")
            or name.endswith(".test.ts")
            or name.endswith(".spec.ts")
            or "/tests/" in str(path).lower()
            or "\\tests\\" in str(path).lower()
        )

    def _is_config_file(self, path: Path):
        return (
            path.name in self.CONFIG_NAMES
            or path.name.startswith(".env")
            or path.name.endswith(".config.js")
            or path.name.endswith(".config.ts")
            or path.name.endswith(".yaml")
            or path.name.endswith(".yml")
        )

    def summary(self, report: RepositoryReport):
        lines = [
            f"Repository: {report.root}",
            f"Files: {report.total_files}",
            f"Total size: {report.total_bytes} bytes",
            "",
            "Languages:",
        ]

        for language, count in sorted(
            report.languages.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            lines.append(
                f"  {language}: {count}"
            )

        lines.append("")
        lines.append(
            f"Test files: {len(report.test_files)}"
        )

        lines.append(
            f"Config files: {len(report.config_files)}"
        )

        lines.append(
            f"Dependency manifests: "
            f"{len(report.dependency_files)}"
        )

        if report.dependency_files:
            lines.append("")
            lines.append("Dependencies:")

            for item in report.dependency_files:
                lines.append(f"  {item}")

        return "\n".join(lines)
