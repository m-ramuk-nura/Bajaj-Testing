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

    # Output the results
    print(f"String s1: '{s1}'")
    print(f"String s2: '{s2}'")
    print(f"Positions where '{s1}' occurs in '{s2}': {positions}")
    print(f"Total occurrences: {len(positions)}")
except Exception as e:
    import traceback
    print('Error:', e)
    print(traceback.format_exc())
