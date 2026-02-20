import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt

# Define fuzzy variables
error = ctrl.Antecedent(np.linspace(-4, 4, 100), 'error')
correction = ctrl.Consequent(np.linspace(-100, 100, 100), 'correction')

# Define membership functions for Error
error['NL'] = fuzz.trimf(error.universe, [-4, -4, -2])
error['NS'] = fuzz.trimf(error.universe, [-4, -2, 0])
error['Z']  = fuzz.trimf(error.universe, [-1, 0, 1])
error['PS'] = fuzz.trimf(error.universe, [0, 2, 4])
error['PL'] = fuzz.trimf(error.universe, [2, 4, 4])

# Define membership functions for Correction
correction['SL'] = fuzz.trimf(correction.universe, [50, 100, 100])
correction['ML'] = fuzz.trimf(correction.universe, [25, 50, 75])
correction['Z']  = fuzz.trimf(correction.universe, [-10, 0, 10])
correction['MR'] = fuzz.trimf(correction.universe, [-75, -50, -25])
correction['SR'] = fuzz.trimf(correction.universe, [-100, -100, -50])

# Define rule base
rule1 = ctrl.Rule(error['NL'], correction['SR'])
rule2 = ctrl.Rule(error['NS'], correction['MR'])
rule3 = ctrl.Rule(error['Z'], correction['Z'])
rule4 = ctrl.Rule(error['PS'], correction['ML'])
rule5 = ctrl.Rule(error['PL'], correction['SL'])

# Create control system
fuzzy_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5])
fuzzy_sim = ctrl.ControlSystemSimulation(fuzzy_ctrl)

# Plot membership functions
error.view()
correction.view()

# Generate surface for visualization
error_range = np.linspace(-4, 4, 50)
correction_output = []

for e in error_range:
    fuzzy_sim.input['error'] = e
    fuzzy_sim.compute()
    correction_output.append(fuzzy_sim.output['correction'])

plt.figure(figsize=(8,4))
plt.plot(error_range, correction_output, 'b')
plt.title('Fuzzy Control Curve (Error → Correction)')
plt.xlabel('Error (line deviation)')
plt.ylabel('Motor Correction (PWM offset)')
plt.grid(True)
plt.show()
