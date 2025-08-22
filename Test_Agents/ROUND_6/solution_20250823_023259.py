try:
    # Given input strings
    s1 = 'ab'
    s2 = 'bddwasabsw'

    # Find the length of s1 and s2
    len_s1 = len(s1)
    len_s2 = len(s2)

    # Initialize the variable to store the maximum overlap
    max_overlap = 0

    # Loop through all possible suffixes of s1
    for i in range(len_s1):
        # Check if the suffix of s1 matches the prefix of s2
        suffix = s1[i:]
        prefix = s2[:len(suffix)]
        if suffix == prefix:
            max_overlap = max(max_overlap, len(suffix))

    # Calculate the shortest combined string
    # by merging s1 and s2 at the maximum overlap
    final_string = s1 + s2[max_overlap:]

    # Output the result
    print("Maximum Overlap:", max_overlap)
    print("Merged String:", final_string)
except Exception as e:
    import traceback
    print('Error:', e)
    print(traceback.format_exc())
