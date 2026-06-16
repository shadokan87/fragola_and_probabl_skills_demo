import csv
from collections import defaultdict

# Read training data
train_data = []
with open('/tmp/train.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        train_data.append(row)

# Read test data
test_data = []
with open('/tmp/test.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        test_data.append(row)

print(f"Train records: {len(train_data)}")
print(f"Test records: {len(test_data)}")

# Simple heuristic-based model
# Rule 1: Women and children first
# Rule 2: First class has higher survival rates
# Rule 3: Higher fare = higher survival rate

def predict_survival(row):
    """
    Predict survival based on simple heuristics
    """
    # Extract features
    sex = row.get('Sex', '').lower()
    pclass = int(row.get('Pclass', 3))
    
    # Try to get age
    age_str = row.get('Age', '')
    age = float(age_str) if age_str else None
    
    # Try to get fare
    fare_str = row.get('Fare', '')
    fare = float(fare_str) if fare_str else None
    
    # Women and children first principle
    if sex == 'female':
        # Female passengers had high survival rate
        if pclass == 1:
            return 1  # First class women almost always survived
        elif pclass == 2:
            return 1  # Second class women had good survival
        else:
            # Third class women had lower but still good rates
            return 1 if (age and age < 10) else 1
    
    # Children had higher survival rates regardless of sex
    if age is not None and age < 10:
        return 1
    
    # Male passengers - lower survival rate
    if sex == 'male':
        if pclass == 1 and fare is not None and fare > 30:
            return 1  # Rich men had better chances
        else:
            return 0  # Most men didn't survive
    
    # Default to 0 if we can't determine
    return 0

# Generate predictions
predictions = []
for row in test_data:
    passenger_id = int(row['PassengerId'])
    survived = predict_survival(row)
    predictions.append((passenger_id, survived))

# Write submission file
with open('/tmp/submission.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['PassengerId', 'Survived'])
    for passenger_id, survived in predictions:
        writer.writerow([passenger_id, survived])

print(f"Submission created with {len(predictions)} predictions")
print(f"Predicted survivors: {sum(p[1] for p in predictions)}")
print(f"Predicted non-survivors: {len(predictions) - sum(p[1] for p in predictions)}")

# Show sample predictions
print("\nSample predictions (first 10):")
with open('/tmp/submission.csv', 'r') as f:
    for i, line in enumerate(f):
        if i <= 10:
            print(line.strip())
