"""A printed name of several tests is a group of runs; synthetic, never NASA data."""

import pytest
from test_document_extraction import entity, submitted
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import (
    Output,
    recover_group_classes,
)
from nasa_fire_ai.ingestion.document_structure import structure

service = _service


SERIES_TEXT = (
    "# Synthetic study\nII. Testing\nSixty test runs were executed (Figure 9).\n"
    "Figure 9 - Pressures During the Sixty Dry Impact Tests to 100 psia\n"
    "Figure 10 - Pressures During the Second Wetted Impact Test Series\n"
    "Run 3 was repeated.\n"
)


@pytest.mark.parametrize(
    "label",
    ["Sixty Dry Impact Tests to 100 psia", "Second Wetted Impact Test Series"],
)
def test_a_printed_name_of_several_tests_is_a_group_whatever_the_proposed_class(service, label):
    p = submitted(service, SERIES_TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "r", label, "ExperimentalRun", label)]
    output, recovered = recover_group_classes(o, structure(p, service.root))
    assert output["entities"][0]["class_id"] == "ExperimentFamily"
    assert recovered["r"]["basis"] == "PRINTED_NAME_OF_SEVERAL_TESTS_IS_A_GROUP"


@pytest.mark.parametrize("label", ["Run 3", "Unprinted Impact Tests"])
def test_one_run_or_an_unprinted_series_name_keeps_its_class(service, label):
    p = submitted(service, SERIES_TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "r", label, "ExperimentalRun", "Run 3 was repeated.")]
    output, recovered = recover_group_classes(o, structure(p, service.root))
    assert output["entities"][0]["class_id"] == "ExperimentalRun"
    assert "r" not in recovered
