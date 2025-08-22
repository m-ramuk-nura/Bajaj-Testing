import subprocess

# Your code as a string
code_str = """# addition.py

# Take two numbers as input
num1 = float(input("Enter first number: "))
num2 = float(input("Enter second number: "))

# Perform addition
result = num1 + num2

# Print the result
print("The sum is:", result)
"""

# Step 1: Save the string to a Python file
file_name = "addition.py"
with open(file_name, "w") as f:
    f.write(code_str)

print(f"✅ Saved code to {file_name}")

# Step 2: Git add, commit, and push using subprocess
try:
    subprocess.run(["git", "add", file_name], check=True)
    subprocess.run(["git", "commit", "-m", "Add addition.py script"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ Code pushed to Git repository")
except subprocess.CalledProcessError as e:
    print(f"⚠️ Git command failed: {e}")
