from fastapi import HTTPException
import pytest

from app.modules.map.service import grid_size_for_zoom, parse_bbox


def test_parse_bbox_valid() -> None:
    bbox = parse_bbox("69.05,54.80,69.25,54.94")
    assert bbox.min_lon == 69.05
    assert bbox.max_lat == 54.94


def test_parse_bbox_rejects_invalid_order() -> None:
    with pytest.raises(HTTPException):
        parse_bbox("69.25,54.80,69.05,54.94")


def test_cluster_grid_gets_smaller_on_higher_zoom() -> None:
    assert grid_size_for_zoom(14) < grid_size_for_zoom(9)
