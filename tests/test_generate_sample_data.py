"""
test_generate_sample_data.py — Unit tests for sample data generators
"""

import pandas as pd
import pytest

from python.generate_sample_data import (
    generate_drug_reference,
    generate_members,
    generate_mtm_interventions,
    generate_patient_safety_gaps,
    generate_pharmacy_claims,
)


class TestGenerateMembers:
    def test_returns_dataframe(self):
        df = generate_members(n=10)
        assert isinstance(df, pd.DataFrame)

    def test_correct_count(self):
        df = generate_members(n=50)
        assert len(df) == 50

    def test_required_columns(self):
        df = generate_members(n=5)
        required = [
            "member_id", "contract_id", "plan_id", "state_code",
            "birth_year", "gender_code", "low_income_subsidy_code",
            "enrollment_start_date", "is_active",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_member_ids_unique(self):
        df = generate_members(n=100)
        assert df["member_id"].nunique() == len(df)

    def test_birth_year_range(self):
        df = generate_members(n=50)
        assert df["birth_year"].between(1900, 2010).all()

    def test_no_phi_in_member_id(self):
        df = generate_members(n=20)
        assert df["member_id"].str.startswith("MBR").all()

    def test_reproducible_with_seed(self):
        df1 = generate_members(n=10, seed=99)
        df2 = generate_members(n=10, seed=99)
        assert df1["member_id"].tolist() == df2["member_id"].tolist()


class TestGeneratePharmacyClaims:
    def setup_method(self):
        self.members = generate_members(n=10)

    def test_returns_dataframe(self):
        df = generate_pharmacy_claims(self.members, n_per_member=5)
        assert isinstance(df, pd.DataFrame)

    def test_claim_count(self):
        df = generate_pharmacy_claims(self.members, n_per_member=5)
        assert len(df) == 50

    def test_required_columns(self):
        df = generate_pharmacy_claims(self.members, n_per_member=3)
        required = [
            "claim_id", "member_id", "contract_id", "ndc",
            "drug_class", "days_supply", "fill_date",
            "pharmacy_npi", "prescriber_npi", "paid_amount",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_claim_ids_unique(self):
        df = generate_pharmacy_claims(self.members, n_per_member=5)
        assert df["claim_id"].nunique() == len(df)

    def test_member_ids_from_members(self):
        df = generate_pharmacy_claims(self.members, n_per_member=3)
        member_ids = set(self.members["member_id"])
        claim_member_ids = set(df["member_id"])
        assert claim_member_ids.issubset(member_ids)

    def test_ndc_format(self):
        df = generate_pharmacy_claims(self.members, n_per_member=3)
        assert df["ndc"].str.len().eq(11).all()

    def test_days_supply_positive(self):
        df = generate_pharmacy_claims(self.members, n_per_member=3)
        assert (df["days_supply"] > 0).all()

    def test_paid_amount_positive(self):
        df = generate_pharmacy_claims(self.members, n_per_member=3)
        assert (df["paid_amount"] > 0).all()


class TestGenerateDrugReference:
    def test_returns_dataframe(self):
        df = generate_drug_reference()
        assert isinstance(df, pd.DataFrame)

    def test_required_columns(self):
        df = generate_drug_reference()
        required = ["ndc", "drug_name", "therapeutic_class", "generic_indicator", "is_high_risk_elderly"]
        for col in required:
            assert col in df.columns

    def test_no_phi(self):
        df = generate_drug_reference()
        assert "member_id" not in df.columns


class TestGenerateMtmInterventions:
    def setup_method(self):
        self.members = generate_members(n=20)

    def test_returns_dataframe(self):
        df = generate_mtm_interventions(self.members)
        assert isinstance(df, pd.DataFrame)

    def test_member_ids_from_members(self):
        df = generate_mtm_interventions(self.members)
        if len(df) > 0:
            member_ids = set(self.members["member_id"])
            assert set(df["member_id"]).issubset(member_ids)

    def test_intervention_ids_unique(self):
        df = generate_mtm_interventions(self.members)
        assert df["intervention_id"].nunique() == len(df)


class TestGeneratePatientSafetyGaps:
    def setup_method(self):
        self.members = generate_members(n=20)

    def test_returns_dataframe(self):
        df = generate_patient_safety_gaps(self.members)
        assert isinstance(df, pd.DataFrame)

    def test_risk_score_range(self):
        df = generate_patient_safety_gaps(self.members)
        if len(df) > 0:
            assert df["risk_score"].between(0.0, 1.0).all()

    def test_gap_ids_unique(self):
        df = generate_patient_safety_gaps(self.members)
        assert df["gap_id"].nunique() == len(df)

    def test_no_phi_in_evidence_summary(self):
        df = generate_patient_safety_gaps(self.members)
        if len(df) > 0:
            import re
            ssn_pattern = r"\d{3}-\d{2}-\d{4}"
            for summary in df["evidence_summary"]:
                assert not re.search(ssn_pattern, summary)
