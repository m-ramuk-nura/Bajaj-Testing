try:
    # Define the input strings
    s1 = 'ab'
    s2 = 'bddwasabsw'

    # Check if s1 is a substring of s2
    result = s1 in s2

    # Print the result
    print(result)
except Exception as e:
    import traceback
    print('Error:', e)
    print(traceback.format_exc())
