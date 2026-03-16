import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# THEORY: We are using a Classifier because 'Focus' is a category (High/Low)
# DESIGN: The model takes 3 inputs (features) to predict 1 output (label)

# 1. Loading the logic (We'll use your real CSV tomorrow!)
# df = pd.read_csv("C:\Users\csmadaab\OneDrive - Liverpool John Moores University\Year 3\Project\Daily Habits and Focus Level Study for Students (Responses) - Form Responses 1.csv")  

# 2. Example Data (What your survey looks like to the computer)
# [Sleep, Stress, ScreenTime]
X = [[8, 2, 1], [4, 8, 6], [7, 5, 2], [5, 7, 4], [9, 1, 0], [3, 9, 7]]
y = [1, 0, 1, 0, 1, 0] # 1 = High Focus, 0 = Low Focus

# 3. Training the Forest
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# 4. Testing a "new" student situation
# (e.g., 6 hours sleep, 6 stress, 3 hours screen time)
test_student = [[6, 6, 3]]
prediction = model.predict(test_student)

if prediction[0] == 1:
    print("Result: High Focus! Schedule: Deep Work session.")
else:
    print("Result: Low Focus. Schedule: Light Admin or Break.")