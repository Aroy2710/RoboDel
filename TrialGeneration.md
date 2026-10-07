For the initial set, using standard iTHOR scenes avoids procedural generation dependencies and allows direct verification of environments, camera coordinates, and object ablations.

Covering the 4 domestic categories with 4 distinct scenes each yields 16 total iTHOR scenes (or 12 if selecting 3 per category):

### 16 Core iTHOR Scenes Setup (4 Scenes × 4 Categories)

| Category | Scene 1 | Scene 2 | Scene 3 | Scene 4 |
| --- | --- | --- | --- | --- |
| **Kitchen** | `FloorPlan5` | `FloorPlan6` | `FloorPlan7` | `FloorPlan8` |
| **Living Room** | `FloorPlan201` | `FloorPlan202` | `FloorPlan203` | `FloorPlan204` |
| **Bedroom** | `FloorPlan301` | `FloorPlan302` | `FloorPlan303` | `FloorPlan304` |
| **Bathroom** | `FloorPlan401` | `FloorPlan402` | `FloorPlan403` | `FloorPlan404` |

---

### Step-by-Step Execution Workflow for Each Scene

For every scene in this set, follow this three-step sequence:

#### 1. Interactive Camera Positioning

Launch `web_explorer.py` to position the camera toward a dense surface (table, counter, desk, or vanity) and note the HUD coordinates:

```bash
python scripts/web_explorer.py 

```

*Note down:* `X`, `Y`, `Z`, `Rotation`, `Horizon`.

#### 2. Probe Visible Target Candidates

Run `batch_pregenerate_2.py` with `--list-objects` to verify visible items from that exact viewpoint:

```bash
python scripts/batch_pregenerate_2.py \
  --dataset-type ithor \
  --scene FloorPlan1 \
  --x <X> --y <Y> --z <Z> --rotY <ROT> --horizon <HOR> \
  --list-objects

```

Select 5 to 8 visible items from the output list (e.g., small appliances, dishware, or tabletop props).

#### 3. Execute Full Batch Generation

Run the full combinatorial permutation generation with `--random-obs` (or explicit `--exclude-obs`):

```bash
python scripts/batch_pregenerate_2.py \
  --dataset-type ithor \
  --scene FloorPlan1 \
  --trial Trial_Kitchen_FP1 \
  --x <X> --y <Y> --z <Z> --rotY <ROT> --horizon <HOR> \
  --targets <TARGET_1> <TARGET_2> <TARGET_3> <TARGET_4> <TARGET_5> \
  --random-obs

```

---

 pseudo-randomized sequence for the 16 iTHOR scenes designed to avoid consecutive room types, keeping visual layouts and themes consistently alternating:

| Run # | Trial Directory | Scene ID | Room Category |
| --- | --- | --- | --- |
| **01** | `Trial_01_LivingRoom_FP202` | `FloorPlan205` | Living Room |
| **02** | `Trial_02_Bathroom_FP403` | `FloorPlan403` | Bathroom |
| **03** | `Trial_03_Kitchen_FP1` | `FloorPlan5` | Kitchen |
| **04** | `Trial_04_Kitchen_FP2` | `FloorPlan6` | Kitchen |
| **05** | `Trial_05_Bedroom_FP304` | `FloorPlan304` | Bedroom |
| **06** | `Trial_06_Bathroom_FP401` | `FloorPlan401` | Bathroom |
| **07** | `Trial_07_LivingRoom_FP204` | `FloorPlan204` | Living Room |
| **08** | `Trial_08_Bedroom_FP301` | `FloorPlan301` | Bedroom |
| **09** | `Trial_09_Bathroom_FP404` | `FloorPlan404` | Bathroom |
| **10** | `Trial_10_Bathroom_FP402` | `FloorPlan402` | Bathroom |
| **11** | `Trial_11_Kitchen_FP3` | `FloorPlan7` | Kitchen |
| **12** | `Trial_12_LivingRoom_FP201` | `FloorPlan201` | Living Room |
| **13** | `Trial_13_Bedroom_FP303` | `FloorPlan303` | Bedroom |
| **14** | `Trial_14_LivingRoom_FP203` | `FloorPlan203` | Living Room |
| **15** | `Trial_15_Kitchen_FP4` | `FloorPlan8` | Kitchen |
| **16** | `Trial_16_Bedroom_FP302` | `FloorPlan302` | Bedroom |
---

# Trial Configs

## Trial 1


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan205 \
  --x -3.7032 --y 0.9011 --z 0.7929 --rotY 29 --horizon 4.2501 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan205 \
  --trial Trial_01_LivingRoom_FP205 \
  --x -3.7032 --y 0.9011 --z 0.7929 --rotY 29 --horizon 4.2501 \
  --targets Laptop Statue Television WateringCan GarbageCan Painting Box DeskLamp FloorLamp HousePlant \
  --random-obs
```
Objects not included in Observation Phase:  GarbageCan , Laptop , Painting , WateringCan
## Trial 2


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan403 \
  --x -0.2276 --y 0.9094 --z 1.457 --rotY 346.4998 --horizon 6.5003 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan403 \
  --trial Trial_02_BathRoom_FP403 \
  --x -0.2276 --y 0.9094 --z 1.457 --rotY 346.4998 --horizon 6.5003 \
  --targets GarbageCan HandTowel Towel SoapBar SoapBottle  Mirror \
  --random-obs
```

Objects not included in Observation Phase : GarbageCan , SoapBar  

## Trial 3


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan5 \
  --x 1.0631 --y 0.901 --z -0.7466 --rotY 267 --horizon -0.5 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan5 \
  --trial Trial_03_Kitchen_FP5 \
  --x 1.0631 --y 0.901 --z -0.7466 --rotY 267 --horizon -0.5 \
  --targets Bowl Bread PaperTowelRoll Cup Kettle Lettuce Mug HousePlant Pot Tomato\
  --random-obs
```

Objects not included in Observation Phase : Bowl, Bread, Kettle , Pot 

## Trial 4


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan6 \
  --x 0.8718 --y 0.901 --z 1.3475 --rotY 200.4191 --horizon 14.0004 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan6 \
  --trial Trial_04_Kitchen_FP6 \
  --x 0.8718 --y 0.901 --z 1.3475 --rotY 200.4191 --horizon 14.0004 \
  --targets Apple Bowl Bread CoffeeMachine Cup Kettle Lettuce PaperTowelRoll Tomato SoapBottle  \
  --random-obs
```

Objects not included in Observation Phase : Apple , CoffeeMachine, SoapBottle 

## Trial 5


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan304 \
  --x 0.188 --y 0.907 --z 0.3278 --rotY 182.25 --horizon 8.2501 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan304 \
  --trial Trial_05_Bedroom_FP304 \
  --x 0.188 --y 0.907 --z 0.3278 --rotY 182.25 --horizon 8.2501\
  --targets AlarmClock Bowl Book Box CellPhone Chair DeskLamp GarbageCan Laptop Mug \
  --random-obs
```

Objects not included in Observation Phase : AlarmClock , Chair, DeskLamp
Done 

## Trial 6


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan401 \
  --x -1.3272 --y 0.9016 --z 0.7827 --rotY 292.9999 --horizon 8.5004 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan401 \
  --trial Trial_06_Bathroom_FP401 \
  --x -1.3272 --y 0.9016 --z 0.7827 --rotY 292.9999 --horizon 8.5004 \
  --targets Candle DishSponge HandTowel PaperTowelRoll SoapBottle ToiletPaper SprayBottle Mirror \
  --random-obs
```

Objects not included in Observation Phase : Mirror , SoapBottle , Towel , Towel Holder 
Done 
## Trial 7


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan204 \
  --x -1.4378 --y 0.9023 --z 3.2359 --rotY 184.9998 --horizon 4.0004 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan204 \
  --trial Trial_07_LivingRoom_FP204 \
  --x -1.4378 --y 0.9023 --z 3.2359 --rotY 184.9998 --horizon 4.0004 \
  --targets Laptop Statue GarbageCan Painting SoapBottle DeskLamp HousePlant Vase KeyChain CreditCard \
  --random-obs
```

Objects not included in Observation Phase : DeskLamp , HousePlant , KeyChain , Laptop , Painting 
Done
## Trial 8


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan301 \
  --x 1.1258 --y 0.9104 --z 0.3383 --rotY 265.7498 --horizon 18.2501 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan301 \
  --trial Trial_08_Bedroom_FP301 \
  --x 1.1258 --y 0.9104 --z 0.3383 --rotY 265.7498 --horizon 18.2501 \
  --targets AlarmClock BasketBall Book Boots CellPhone DeskLamp Laptop Pillow Statue DogBed \
  --random-obs
```

Objects not included in Observation Phase : Statue , Book
 Done 
## Trial 9


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan404 \
  --x -2.7978 --y 0.9032 --z 1.7009 --rotY 121.7499 --horizon 22.0001 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan404 \
  --trial Trial_09_Bathroom_FP404 \
  --x -2.7978 --y 0.9032 --z 1.7009 --rotY 121.7499 --horizon 22.0001 \
  --targets Candle Towel GarbageCan HandTowel Plunger ScrubBrush SoapBar SprayBottle TissueBox Cloth \
  --random-obs
```

Objects not included in Observation Phase : GarbageCan TissueBox 


## Trial 10


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan402 \
  --x -1.7317 --y 0.9007 --z 2.173 --rotY 4.9999 --horizon 9.0002 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan402 \
  --trial Trial_10_Bathroom_FP402 \
  --x -1.7317 --y 0.9007 --z 2.173 --rotY 4.9999 --horizon 9.0002 \
  --targets Candle GarbageCan HandTowel Plunger ScrubBrush SoapBottle LightSwitch\
  --random-obs
```

Objects not included in Observation Phase : GarbageCan , HandTowel ScrubBrush
Done

## Trial 11


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan7 \
  --x 0.5275 --y 0.901 --z -0.5127 --rotY 272.4999 --horizon -2 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan7 \
  --trial Trial_11_Kitchen_FP7 \
  --x 0.5275 --y 0.901 --z -0.5127 --rotY 272.4999 --horizon -2 \
  --targets Apple Bread Bowel CoffeeMachine Cup Kettle Lettuce GarbageCan HousePlant Pot Book\
  --random-obs
```

Objects not included in Observation Phase : Book , Bread , HousePlant , Kettle  


## Trial 12


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan201 \
  --x -4.184 --y 0.9027 --z 1.3466 --rotY 90.75 --horizon 12 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan201 \
  --trial Trial_12_LivingRoom_FP201 \
  --x -4.184 --y 0.9027 --z 1.3466 --rotY 90.75 --horizon 12 \
  --targets Book CreditCard Laptop Statue Painting DeskLamp FloorLamp HousePlant Newspaper RemoteControl\
  --random-obs
```

Objects not included in Observation Phase : CreditCard , FloorLamp , Newspaper 


## Trial 13


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan303 \
  --x 0.9332 --y 0.901 --z -0.5238 --rotY 236.7496 --horizon 10.2501 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan303 \
  --trial Trial_13_Bedroom_FP303 \
  --x 0.9332 --y 0.901 --z -0.5238 --rotY 236.7496 --horizon 10.2501 \
  --targets AlarmClock BaseballBat Book DeskLamp Laptop Pillow Poster Vase Mug CellPhone\
  --random-obs
```

Objects not included in Observation Phase : Mirror , SoapBottle , Towel , Towel Holder 


## Trial 14


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan203 \
  --x -2.222 --y 0.9071 --z 4.8928 --rotY 110.9997 --horizon 4.5002 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan203 \
  --trial Trial_14_LivingRoom_FP203 \
  --x -2.222 --y 0.9071 --z 4.8928 --rotY 110.9997 --horizon 4.5002 \
  --targets Laptop HousePlant Painting Box FloorLamp Newspaper Ottoman Pillow Television RemoteControl\
  --random-obs
```

Objects not included in Observation Phase : Box , HousePlant , Newspaper , Painting , Pillow 

## Trial 15


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan8 \
  --x -0.9018 --y 0.901 --z -0.0471 --rotY 119.9999 --horizon 11.5002 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan8 \
  --trial Trial_15_Kitchen_FP8 \
  --x -0.9018 --y 0.901 --z -0.0471 --rotY 119.9999 --horizon 11.5002 \
  --targets Apple Bowl Bread Bottle CoffeeMachine GarbageCan HousePlant Kettle SoapBottle Cup\
  --random-obs
```

Objects not included in Observation Phase : Bottle,  Bowl , Cup , GarbageCan

## Trial 16


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan302 \
  --x -0.1382 --y 0.901 --z 0.4646 --rotY 178.25 --horizon 19.0001 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan302 \
  --trial Trial_16_Bedroom_FP302 \
  --x -0.1382 --y 0.901 --z 0.4646 --rotY 178.25 --horizon 19.0001 \
  --targets AlarmClock Book Bowl CellPhone HousePlant Laptop Painting Pillow TeddyBear CreditCard\
  --random-obs
```

Objects not included in Observation Phase : CreditCard ,  HousePlant , Book