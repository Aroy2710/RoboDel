import json

# Load the cohort telemetry dataset
with open("master_dataset.json", "r") as f:
    data = json.load(f)

# Ground-truth mapping of trial index to the exact list of distractor objects
# artificially introduced during the Interactive Phase (parsed from TrialGeneration.md)
distractor_lists = {
    0: ["garbagecan", "laptop", "painting", "wateringcan"],
    1: ["garbagecan", "soapbar"],
    2: ["bowl", "bread", "kettle", "pot"],
    3: ["apple", "coffeemachine", "soapbottle"],
    4: ["alarmclock", "chair", "desklamp"],
    5: ["mirror", "soapbottle", "towel", "towelholder"], 
    6: ["desklamp", "houseplant", "keychain", "laptop", "painting"],
    7: ["statue", "book"],
    8: ["garbagecan", "tissuebox"],
    9: ["garbagecan", "handtowel", "soapbottle", "toiletpaper", "toiletpaperhanger"],
    10: ["coffeemachine", "lettuce", "pot"],
    11: ["creditcard", "floorlamp", "newspaper"],
    12: ["baseballbat", "laptop", "mug", "pillow"],
    13: ["painting", "pillow", "remotecontrol"],
    14: ["dishsponge", "houseplant", "pot"],
    15: ["cellphone", "houseplant", "pillow"]
}

# Define the valid analysis cohort
valid_participants = ["1", "2", "3", "5", "6", "7"]

total_distractors = 0
total_correctly_deleted = 0
total_false_positives = 0
total_trials = 0

for session in data["sessions"]:
    participant_id = session.get("participant_id")
    
    # Filter for valid cohort members
    if participant_id in valid_participants:
        trial_index = session.get("trial_index")
        
        # Extract lowercased base labels of the objects the participant actively deleted
        removed_labels = [label.split('_')[0].lower() for label in session.get("removed_labels", [])]
        
        # Isolate the expected distractors for this specific trial
        expected_labels = list(distractor_lists.get(trial_index, []))
        
        distractor_count = len(expected_labels)
        total_distractors += distractor_count
        
        correct_deletions = 0
        false_positives = 0
        
        # Evaluate transsaccadic memory recall fidelity
        for label in removed_labels:
            if label in expected_labels:
                correct_deletions += 1
                # Remove from expected list to prevent duplicate counting
                expected_labels.remove(label)
            else:
                false_positives += 1
                
        total_correctly_deleted += correct_deletions
        total_false_positives += false_positives
        total_trials += 1

# Compute final cohort behavioral metrics
average_distractors_per_trial = total_distractors / total_trials if total_trials > 0 else 0
average_correctly_deleted_per_trial = total_correctly_deleted / total_trials if total_trials > 0 else 0
accuracy = (total_correctly_deleted / total_distractors) * 100 if total_distractors > 0 else 0

print(f"Total Valid Trials Analyzed: {total_trials}")
print(f"Average Distractors per Trial: {average_distractors_per_trial:.2f}")
print(f"Average Correctly Deleted per Trial: {average_correctly_deleted_per_trial:.2f}")
print(f"Mean False-Positive Rejection Accuracy: {accuracy:.1f}%")