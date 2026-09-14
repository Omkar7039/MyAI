from experience.provenance import ExperienceProvenance


def test_experience_provenance():
    verified = ExperienceProvenance(
        source="repair",
        workflow="repair_and_verify",
        evidence=(
            "regression tests passed",
            "mutation verification passed",
            "property verification passed",
        ),
        verified=True,
    )

    unverified = ExperienceProvenance(
        source="debug",
        workflow="analysis",
        evidence=(),
        verified=False,
    )

    assert verified.has_evidence
    assert verified.evidence_text
    assert verified.verified
    assert verified.to_metadata()["source"] == "repair"
    assert verified.to_metadata()["verified"] is True

    assert not unverified.has_evidence
    assert unverified.evidence_text == ""
    assert not unverified.verified
