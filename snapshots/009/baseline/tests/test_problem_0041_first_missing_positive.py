from problems.problem_0041_first_missing_positive import first_missing_positive


def test_all_negative():
    assert first_missing_positive([-1, -2, -3]) == 1


def test_with_duplicates():
    assert first_missing_positive([1, 1, 2, 2, 3, 3]) == 4


def test_missing_at_end():
    assert first_missing_positive([1, 2, 3, 4]) == 5
