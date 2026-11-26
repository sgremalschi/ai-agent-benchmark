def first_missing_positive(nums: list[int]) -> int:
    if not nums:
        return 1

    i = 0
    while i < len(nums):
        if nums[i] < 1 or nums[i] > len(nums):
            i += 1
        elif nums[nums[i] - 1] != nums[i]:
            tmp = nums[nums[i] - 1]
            nums[nums[i] - 1] = nums[i]
            nums[i] = tmp
        else:
            i += 1

    i = 0
    while i < len(nums):
        if nums[i] != i + 1:
            return i + 1
        i += 1

    return i + 1
