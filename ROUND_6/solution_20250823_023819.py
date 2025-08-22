try:
    # Given strings
    s1 = 'ab'
    s2 = 'bddwasabsw'

    # Find all occurrences of s1 in s2
    positions = []
    start = 0
    while True:
        index = s2.find(s1, start)
        if index == -1:
            break
        positions.append(index)
        start = index + 1

    # Calculate results
    total_occurrences = len(positions)
    positions_list = positions

    # Output the results
    print(f"String s1: '{s1}'")
    print(f"String s2: '{s2}'")
    print(f"Total occurrences of s1 in s2: {total_occurrences}")
    print(f"Starting positions of each occurrence: {positions_list}")
except Exception as e:
    import traceback
    print('Error:', e)
    print(traceback.format_exc())
