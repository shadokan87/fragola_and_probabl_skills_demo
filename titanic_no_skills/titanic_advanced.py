import csv
import math
from collections import defaultdict

# Read data
def read_csv(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

train_data = read_csv('/tmp/train.csv')
test_data = read_csv('/tmp/test.csv')

print(f"Training set size: {len(train_data)}")
print(f"Test set size: {len(test_data)}")

# Calculate statistics for better predictions
def get_float_or_none(val, default=None):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

# Calculate survival rates by group
survival_by_sex_pclass = defaultdict(lambda: {'survived': 0, 'total': 0})
avg_age_by_pclass = defaultdict(list)
avg_fare_by_pclass = defaultdict(list)

for row in train_data:
    sex = row.get('Sex', '').lower()
    pclass = row.get('Pclass', '3')
    survived = int(row.get('Survived', 0))
    age = get_float_or_none(row.get('Age', ''))
    fare = get_float_or_none(row.get('Fare', ''))
    
    key = (sex, pclass)
    survival_by_sex_pclass[key]['survived'] += survived
    survival_by_sex_pclass[key]['total'] += 1
    
    if age is not None:
        avg_age_by_pclass[pclass].append(age)
    if fare is not None:
        avg_fare_by_pclass[pclass].append(fare)

# Calculate means
age_means = {pclass: sum(ages) / len(ages) if ages else 30 
             for pclass, ages in avg_age_by_pclass.items()}
fare_means = {pclass: sum(fares) / len(fares) if fares else 30 
              for pclass, fares in avg_fare_by_pclass.items()}

print("\nSurvival rates by Sex and Class:")
for (sex, pclass), stats in sorted(survival_by_sex_pclass.items()):
    rate = stats['survived'] / stats['total'] if stats['total'] > 0 else 0
    print(f"  {sex.capitalize()} Class {pclass}: {rate:.2%} ({stats['survived']}/{stats['total']})")

print("\nAverage age by class:", age_means)
print("Average fare by class:", fare_means)

# Improved prediction function
def predict_survival_v2(row, age_means, fare_means, survival_by_sex_pclass):
    sex = row.get('Sex', '').lower()
    pclass = row.get('Pclass', '3')
    
    age = get_float_or_none(row.get('Age', ''))
    if age is None:
        age = age_means.get(pclass, 30)
    
    fare = get_float_or_none(row.get('Fare', ''))
    if fare is None:
        fare = fare_means.get(pclass, 30)
    
    # Get baseline survival probability for this group
    key = (sex, pclass)
    if key in survival_by_sex_pclass:
        base_prob = survival_by_sex_pclass[key]['survived'] / survival_by_sex_pclass[key]['total']
    else:
        base_prob = 0.5
    
    # Adjust based on age (children had better survival)
    if age < 10:
        base_prob = min(1.0, base_prob * 1.5)
    elif age < 18:
        base_prob = min(1.0, base_prob * 1.2)
    elif age > 60:
        base_prob = max(0, base_prob * 0.7)
    
    # Adjust based on fare (higher fare = higher survival)
    fare_threshold = fare_means.get(pclass, 30)
    if fare > fare_threshold * 1.5:
        base_prob = min(1.0, base_prob * 1.2)
    elif fare < fare_threshold * 0.5:
        base_prob = max(0, base_prob * 0.8)
    
    return 1 if base_prob > 0.5 else 0

# Make predictions
predictions = []
for row in test_data:
    passenger_id = int(row['PassengerId'])
    survived = predict_survival_v2(row, age_means, fare_means, survival_by_sex_pclass)
    predictions.append((passenger_id, survived))

# Write submission
with open('/tmp/submission.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['PassengerId', 'Survived'])
    for passenger_id, survived in predictions:
        writer.writerow([passenger_id, survived])

print(f"\nSubmission saved!")
print(f"Total predictions: {len(predictions)}")
print(f"Predicted survivors: {sum(p[1] for p in predictions)}")
print(f"Predicted non-survivors: {len(predictions) - sum(p[1] for p in predictions)}")

# Show first 20 predictions
print("\nFirst 20 predictions:")
for i, (pid, survived) in enumerate(predictions[:20]):
    print(f"  PassengerId {pid}: {'Survived' if survived else 'Died'}")
