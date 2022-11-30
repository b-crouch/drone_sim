# drone_sim
A multiphysics engine to simulate drone swarm behavior

This scripts simulates the dynamics of a drone swarm attempting to capture stationary targets while avoiding moving antagonistic obstacles. The engine has two components:
* Base implementation of drone trajectories over time as they seek targets while acted upon by propoulsive and drag forces
* Genetic algorithm designed to select optimal parameters for driving drone behavior to balance the competing goals of making contact with targets while avoiding obstacles
