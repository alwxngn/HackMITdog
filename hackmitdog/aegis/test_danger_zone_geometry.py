"""Standalone unit tests for danger_zone.py's geometry math.

No DimOS import needed -- ``point_in_polygon``/``distance_to_polygon`` are
plain-stdlib functions, independent of the ``Module``/``@skill`` machinery
around them. Runs under pytest (``pytest hackmitdog/aegis/test_danger_zone_geometry.py``)
or directly (``python hackmitdog/aegis/test_danger_zone_geometry.py``).
"""

from __future__ import annotations

from hackmitdog.aegis.danger_zone import distance_to_polygon, point_in_polygon

# A simple axis-aligned 4x4 square, corners at (0,0)-(4,0)-(4,4)-(0,4).
_SQUARE = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]


def test_point_clearly_inside_square() -> None:
    assert point_in_polygon(2.0, 2.0, _SQUARE) is True


def test_point_clearly_outside_square() -> None:
    assert point_in_polygon(10.0, 10.0, _SQUARE) is False
    assert point_in_polygon(-1.0, 2.0, _SQUARE) is False


def test_point_on_edge_boundary_convention() -> None:
    """Document this module's ray-casting boundary convention.

    Ray casting (even-odd rule) does not treat "exactly on an edge" as a
    distinct third state -- the result depends on which edge and the ray
    direction, a well-known property of the algorithm (see
    ``point_in_polygon``'s own docstring). This test pins down the actual
    behavior for this polygon's edges so a future change is caught, not to
    claim it's the only valid convention.
    """
    # Point on the bottom edge (y=0): this implementation's half-open
    # crossing test ``(y1 > y) != (y2 > y)`` treats the bottom-left corner's
    # y (0) as "not above" the ray, so the left edge (y: 0->4) counts as a
    # crossing while the bottom edge (y: 0->0, horizontal) never does. Net
    # result for this square: bottom- and left-edge points read as inside;
    # top- and right-edge points read as outside. Pinned down here so a
    # future change to the algorithm is caught, not to claim this is the
    # only valid convention -- see the caveat in point_in_polygon's docstring.
    assert point_in_polygon(2.0, 0.0, _SQUARE) is True  # bottom edge
    assert point_in_polygon(0.0, 2.0, _SQUARE) is True  # left edge
    assert point_in_polygon(2.0, 4.0, _SQUARE) is False  # top edge
    assert point_in_polygon(4.0, 2.0, _SQUARE) is False  # right edge

    # Point on the right edge (x=4, y=2): distance_to_danger_zone's contract
    # (distance == 0 for inside-or-on-boundary) is the authoritative way to
    # ask "is this on the line", per point_in_polygon's own docstring.
    on_right_edge_distance = distance_to_polygon(4.0, 2.0, _SQUARE)
    assert on_right_edge_distance == 0.0


def test_distance_outside_one_edge_by_hand() -> None:
    """A point 2m directly outside the square's right edge (x=4)."""
    # Point (6, 2) is 2m to the right (+x) of the nearest boundary point
    # (4, 2), which lies on the right edge (x=4, 0<=y<=4).
    distance = distance_to_polygon(6.0, 2.0, _SQUARE)
    assert abs(distance - 2.0) < 1e-9


def test_distance_zero_inside() -> None:
    assert distance_to_polygon(2.0, 2.0, _SQUARE) == 0.0


def test_distance_from_corner_diagonal() -> None:
    """A point 3-4-5 triangle away from the nearest corner."""
    # Nearest point to (7, 4) on the square is corner (4, 4): distance 3.
    # Nearest point to (4, 8) on the square is corner (4, 4): distance 4.
    assert abs(distance_to_polygon(7.0, 4.0, _SQUARE) - 3.0) < 1e-9
    assert abs(distance_to_polygon(4.0, 8.0, _SQUARE) - 4.0) < 1e-9


def test_triangle_polygon() -> None:
    """Sanity check on a non-square (non-axis-aligned-edges) polygon."""
    triangle = [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]
    assert point_in_polygon(1.0, 1.0, triangle) is True
    assert point_in_polygon(3.0, 3.0, triangle) is False
    assert distance_to_polygon(1.0, 1.0, triangle) == 0.0


if __name__ == "__main__":
    tests = [
        test_point_clearly_inside_square,
        test_point_clearly_outside_square,
        test_point_on_edge_boundary_convention,
        test_distance_outside_one_edge_by_hand,
        test_distance_zero_inside,
        test_distance_from_corner_diagonal,
        test_triangle_polygon,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
