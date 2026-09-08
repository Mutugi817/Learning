# 1. Standard Python list
# Dynamic size, herogeneous types (stores refrences to objects)
arr_list = [10, 20, 30, 40, 50]


# 2. Built in array module (Homogeneous C - style array)
# Dynamic size, enforced single c data type ('i' represents a single integer)
import array
arr_typed = array.array('i', [10, 20, 30, 40, 50])


# 3. NumPy Array(closest to c in lowlevel behaviour)
# Fixed size upon creation, contiguous bloc of memory for high performance
# import numpy as np // Must be installed first
# arr_np = np.array([10, 20, 30, 40, 50], dtype = int)

# print(arr_np)

# ARRAY OPERATIONS
# 1. Traverse
LA = [1, 3, 5, 7,8]
n = len(LA)

print("Here are the elements in the array:")
for i in range(n): 
    print(f"LA[{i}] = {LA[i]}")

# 2. Insert Operation 
item = 10 # Element to insert
k = 3 # Target index position

# Step 1: Shift elements to te right start from the tail
j = n - 1
while j >= k:
    LA[j + 1] = LA[j]
    j -= 1

# Step 2: Insert item
LA[k] = item

print("Array after insertion: ")
for i in range(n):
    print(f"LA[{i}] = {LA[i]}")
