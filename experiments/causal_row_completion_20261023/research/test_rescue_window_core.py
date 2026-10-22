from rescue_window_core import subtract

def test_private_flight_is_not_free_parallel_generation():
    assert subtract([(1,5)],[(0,2),(3,4)])==[(2,3),(4,5)]

def test_intersecting_owner_and_private_blocks_not_double_subtracted():
    assert subtract([(1,5)],[(2,4),(3,4.5)])==[(1,2),(4.5,5)]

def test_no_negative_window_or_implicit_deadline_extension():
    assert subtract([(1,2)],[(0,3)])==[]
