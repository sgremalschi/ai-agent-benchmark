from problems.problem_0452_minimum_number_arrows import Solution


def test_empty():
    assert Solution().findMinArrowShots([]) == 0


def test_single_balloon():
    assert Solution().findMinArrowShots([[1, 2]]) == 1
