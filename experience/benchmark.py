from __future__ import annotations

from dataclasses import asdict
import json

from experience.scorecard import ExperienceScorecardRunner


class ExperienceBenchmark:
    """Generate a deterministic baseline report for experience memory."""

    def __init__(self, runner=None):
        self.runner = runner or ExperienceScorecardRunner()

    def run(self) -> dict:
        scorecard = self.runner.run()

        return {
            "benchmark": "experience-memory-baseline",
            "metrics": asdict(scorecard),
        }

    def render(self, result: dict) -> str:
        metrics = result["metrics"]

        lines = [
            "MYAI EXPERIENCE MEMORY BASELINE",
            "",
            f"Retrieval:       {metrics['retrieval']:.2f}",
            f"Applicability:   {metrics['applicability']:.2f}",
            f"Confidence:      {metrics['confidence']:.2f}",
            f"Contradiction:   {metrics['contradiction']:.2f}",
            f"Consolidation:   {metrics['consolidation']:.2f}",
            f"Project scoping: {metrics['project_scoping']:.2f}",
            f"Overall:         {metrics['overall']:.2f}",
        ]

        return "\n".join(lines)

    def to_json(self, result: dict) -> str:
        return json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
